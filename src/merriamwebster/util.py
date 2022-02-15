import re
import requests
import logging

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

    # add a colon when there are 2 links together
    clean_text = re.sub(":\w\|\|.*?}\s{.*?\|", " : ", clean_text)
    clean_text = re.sub("\|\|.*?}\s{.*?\|", " : ", clean_text)

    # remove link markings: {a_link}, {d_link}, {dxt}, {et_link}, {i_link}, {mat}, {sx}
    # remove cross references: {dx}, {dx_def}, {dx_ety}, {ma}
    # note the only example found in test words were {sx} - assume the format
    # is the same for other links
    clean_text = re.sub('{.*?\|', "", clean_text)
    clean_text = re.sub(":\w\|\|.*?}", "", clean_text)
    clean_text = re.sub("\|\|.*?}", "", clean_text)

    # anything else left in curly brackets will be removed
    # work markings and gloss tokens: {gloss}, {parahw}, {phrase}, {qword}, {wi}
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


def extract_definition(def_content, offensive_note):
    meaning = dict()
    examples = list()

    if offensive_note:
        clean_def = "[" + offensive_note + "] "
    else:
        clean_def = ""

    def_dict = dict(def_content)
    for ky, vl in def_dict.items():
        if vl is not None:
            #logging.debug('MW: The def_instance: (key, value)', ky, vl)
            # if this is a text check to see if there are any other parts to concat
            if ky == 'text':
                clean_def = clean_def + clean_string(vl)
            # if this is a vis (example) then parse and clean the list of examples
            elif ky == 'vis':
                # only extract examples if there is a definition
                if clean_def:
                    examples = extract_examples(vl)
            # uns - usage note - no conversion
            elif ky == 'uns':
                logging.debug('MW: Found uns: %s', vl)
            # if this is a g then concat with the text
            elif ky == 'g':
                clean_def = clean_def + vl
            # if this is another tag not accounted for - log these items
            # bnw - biographical name wrap
            # ca - called also
            # snote - supplemental note
            else:
                logging.error('MW: Found an uncaught definition instance: %s', vl)
        else:
            logging.error("MW: value in definition dictionary is none")

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

        # loop through the list of data returned from MW
        for definition_entry in word_data:

            # If this definition is not quite right it won't have the meta tag
            if 'meta' in definition_entry:
                # clean any syllable markers (asterisk) from headword
                # remove anything inside curly brackets
                #   example is N-allylnormorphine "hw":"{bit}N{\/bit}-al*lyl*nor*mor*phine"
                if definition_entry["hwi"]["hw"]:
                    clean_headword = definition_entry["hwi"]["hw"].replace("*", "")
                    clean_headword = re.sub("{.*?}", "", clean_headword)

                    meaning = ""
                    if clean_headword == word:
                        mw_dictionary_result["headword"] = clean_headword

                        if 'fl' in definition_entry:
                            # get the part of speech
                            pos = definition_entry["fl"]

                            # for this pos, extract a list of meanings with examples
                            # get the defining text(dt) found at [def][sseq][sense][dt]
                            # offensive info is sibling to dt [def][sseq][sense][sls]
                            for def_instance in definition_entry['def']:
                                for def_sseq in def_instance.values():
                                    for def_sense in def_sseq:
                                        for sense_element in def_sense:
                                            offensive_note = ""
                                            for k, v in sense_element[1].items():
                                                # sls is a string of notes with offensive info
                                                # assumption that this is always before dt
                                                if k == 'sls':
                                                    for sls_val in v:
                                                        if 'offensive' in sls_val:
                                                            offensive_note = sls_val
                                                            logger.debug("MW: found offensive indicator:", offensive_note)
                                                elif k == 'dt':
                                                    meaning = extract_definition(v, offensive_note)
                                            if meaning:
                                                meaning["pos"] = pos
                                                # only append the pos if there is a definition
                                                meanings.append(meaning)
                                    mw_dictionary_result["meanings"] = meanings
                        else:
                            logging.error("MW: Skipping this POS - no def ", clean_headword)
                else:
                    logging.error('MW: Skipping, No Headword found')
            else:
                logging.error('MW: Skipping, No Meta - Not a word in intermediate dictionary')
                return None

    if mw_dictionary_result:
        return mw_dictionary_result
    else:
        return None
