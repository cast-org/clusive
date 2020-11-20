#!/usr/bin/env python
import json
import os
import sys

from lemminflect import Lemmatizer

## Test a couple of different methods of extracing base forms from inflected words.
## This tests two methods against all the glossary headwords.

def main() -> None:
    for file in sys.argv[1:]:
        if os.path.exists(file):
            print('File: ', file)
            unchanged: list
            unchanged = []
            with open(file, 'r', encoding='utf-8') as f:
                glossary = json.load(f)
                for e in glossary:
                    hw = e['headword']
                    old_base = base_form(hw)
                    new_base = new_base_form(hw)
                    if hw == old_base and hw == new_base:
                        unchanged.append(hw)
                    elif old_base == new_base:
                        print('  %s -> %s' % (hw, new_base))
                    else:
                        print('  %s -> %s -> NEW %s' % (hw, old_base, new_base))
                # print('  Unchanged: ', ', '.join(unchanged))
        else:
            print('No such file: ', file)


def new_base_form(word):
    wl = word.lower()
    all_forms = set()
    for pos, lemmas in getAllLemmas(wl).items():
        # logger.debug("%s as %s simplifies to %s", wl, pos, lemmas)
        all_forms.add(lemmas[0])   # NEW - ONLY INCLUDE FIRST OPTION
    # There may be multiple base forms for a word, eg "outing" is base form of noun, but inflected form of verb "out".
    # We somewhat arbitrarily choose the shortest one.
    if all_forms:
        return min(all_forms, key=base_form_sort_key)
    else:
        return wl


def base_form(word):
    wl = word.lower()
    all_forms = set()
    for pos, lemmas in getAllLemmas(wl).items():
        # logger.debug("%s as %s simplifies to %s", wl, pos, lemmas)
        all_forms.update(lemmas)
    # There may be multiple base forms for a word, eg "outing" is base form of noun, but inflected form of verb "out".
    # We somewhat arbitrarily choose the shortest one.
    if all_forms:
        return min(all_forms, key=base_form_sort_key)
    else:
        return wl

def getAllLemmas(word, upos=None):
    return Lemmatizer().getAllLemmas(word, upos)

def base_form_sort_key(word):
    # We sort by length primarily, so that the shortest potential base form will be returned.
    # Within length, sort alphabetically. Needed so that return value is deterministic even with multiple,
    # same-length base forms possible  (eg "more" -> "more" or "much")
    return "%03d%s" % (len(word), word)

if __name__ == "__main__":
    main()
