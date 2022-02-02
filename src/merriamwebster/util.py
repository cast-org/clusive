import logging
import re

import requests

from clusive_project import settings

logger = logging.getLogger(__name__)


def find_in_dictionary(word):
    if settings.MERRIAM_WEBSTER_API_KEY is not None and settings.MERRIAM_WEBSTER_API_KEY:
        api_key = settings.MERRIAM_WEBSTER_API_KEY
        api_url = 'https://www.dictionaryapi.com/api/v3/references/sd3/json/'
        api_call = api_url + word + '?key=' + api_key
        try:
            r = requests.get(api_call)
        except requests.exceptions.RequestException as e:
            logging.error('MW: Error Calling API : %s', e)
            return None
        if r:
            try:
                return r.json()
            except ValueError as error:
                logging.error('MW: Error creating json : %s. API response: %s', error, r.text)
                return None
        else:
            return None
    else:
        return None


def json_extract(obj, key):
    # Recursively fetch values from nested JSON.
    arr = []

    def extract(loop_obj, loop_arr, loop_key):
        # Recursively search for values of key in JSON tree.
        if isinstance(loop_obj, dict):
            for k, v in loop_obj.items():
                if k == loop_key:
                    loop_arr.append(v)
                elif isinstance(v, (dict, list)):
                    extract(v, loop_arr, loop_key)
        elif isinstance(loop_obj, list):
            for item in loop_obj:
                extract(item, loop_arr, loop_key)
        return loop_arr

    values = extract(obj, arr, key)
    return values


def clean_string(some_text):
    clean_text = some_text

    # formatting and punctuation: {b}, {bc}, {inf}, {it}, {ldquo}, {p_br), {rdquo}, {sc}, {sup}
    # reformat bold markings
    clean_text = re.sub("{b}", "<b>", clean_text)
    clean_text = re.sub("{/b}", "</b>", clean_text)

    # delete any leading {bc} - output a bold colon and a space
    clean_text = re.sub("^{bc}", "", clean_text)
    # any internal {bc} gets replaced with :
    clean_text = re.sub("{bc}", ": ", clean_text)

    # reformat sub/super script markings
    clean_text = re.sub("{inf}", "<sub>", clean_text)
    clean_text = re.sub("{/inf}", "</sub>", clean_text)
    clean_text = re.sub("{sup}", "<sup>", clean_text)
    clean_text = re.sub("{/sup}", "</sup>", clean_text)

    # reformat italics markings
    clean_text = re.sub("{it}", "<i>", clean_text)
    clean_text = re.sub("{/it}", "</i>", clean_text)

    # remove left & right quote markings
    clean_text = re.sub("{ldquo}", "&ldquo;", clean_text)
    clean_text = re.sub("{rdquo}", "&rdquo;", clean_text)

    # insert a break
    clean_text = re.sub("{p_br}", "<br>", clean_text)

    # remove link markings: {a_link}, {d_link}, {dxt}, {et_link}, {i_link}, {mat}, {sx}
    # remove cross references: {dx}, {dx_def}, {dx_ety}, {ma}
    # note the only example found in test words were {sx} - assume the format
    # is the same for other links
    clean_text = re.sub('{.*?\|', "", clean_text)
    clean_text = re.sub("\|\|.*?}", "", clean_text)

    # anything else left in curly brackets will be removed
    # work markings and gloss tokens: {gloss}, {parahw}, {phrase}, {qword}, {wi}
    # TODO: log these items?
    clean_text = re.sub("{.*?}", "", clean_text)

    return clean_text


def extract_examples(examples):
    # return a list of strings
    clean_examples = list()

    # examples are dictionaries - extract the key 't'
    for example in examples:
        if example['t']:
            clean_example = clean_string(example['t'])
            clean_examples.append(clean_example)

    return clean_examples


def extract_definition(def_content):
    clean_def = ""
    meaning = dict()
    examples = list()

    for def_instance in def_content:
        logging.debug('MW: The def_instance: %s', def_instance)
        if len(def_instance) > 1 and def_instance[1] is not None:
            # if this is a text check to see if there are any other parts to concat
            if def_instance[0] == 'text':
                clean_def = clean_def + clean_string(def_instance[1])
            # if this is a vis (example) then parse and clean the list of examples
            elif def_instance[0] == 'vis':
                examples = extract_examples(def_instance[1])
            # uns - usage note - no conversion
            elif def_instance[0] == 'uns':
                logging.debug('MW: Found uns: %s', def_instance[1])
            # if this is a g then concat with the text
            elif def_instance[0] == 'g':
                clean_def = clean_def + def_instance[1]
            # if this is another tag not accounted for - log these items
            # bnw - biographical name wrap
            # ca - called also
            # snote - supplemental note
            else:
                logging.error('MW: Found an uncaught definition instance: %s', def_instance)
        else:
            logging.error('MW: Found an uncaught definition instance: %s', def_instance)

    if clean_def:
        meaning["definition"] = clean_def
    if examples:
        meaning["examples"] = examples
    return meaning


def lookup(word: str):
    """
    Look up a word in the Merriam-Webster dictionary API and return a definition structure.
    If the word is not found, return None.
    :param word: base form of the word to look up
    :return: python object in Clusive's standard glossary format.
    """
    word_data = find_in_dictionary(word)
    if word_data is None:
        return None
    else:
        mw_dictionary_result = dict()
        meanings = list()
        for definition_entry in word_data:
            # clean any syllable markers (asterisk) from headword
            # remove anything inside curly brackets
            #   example is N-allylnormorphine "hw":"{bit}N{\/bit}-al*lyl*nor*mor*phine"
            if definition_entry["hwi"]["hw"]:
                clean_headword = definition_entry["hwi"]["hw"].replace("*", "")
                clean_headword = re.sub("{.*?}", "", clean_headword)

                if clean_headword == word:
                    mw_dictionary_result["headword"] = clean_headword

                    if 'fl' in definition_entry:
                        # get the part of speech
                        pos = definition_entry["fl"]

                        # for this pos, extract a list of meanings with examples
                        json_dt = json_extract(definition_entry, 'dt')

                        for def_content in json_dt:
                            meaning = extract_definition(def_content)
                            meaning["pos"] = pos
                            if meaning:
                                meanings.append(meaning)
                        mw_dictionary_result["meanings"] = meanings
                    else:
                        logging.debug('MW: No POS found - skip')
            else:
                logging.debug('MW: No Headword found - skip')
                return None
        if mw_dictionary_result:
            logging.debug('MW: results: %s', mw_dictionary_result)
            return mw_dictionary_result
        else:
            return None
