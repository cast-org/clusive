import string

import requests
import json
import re


def json_extract(obj, key):
    # Recursively fetch values from nested JSON.
    arr = []
    def extract(obj, arr, key):
        # Recursively search for values of key in JSON tree.
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key:
                    #print('FOUND A DT MATCH')
                    arr.append(v)
                elif isinstance(v, (dict, list)):
                    extract(v, arr, key)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    values = extract(obj, arr, key)
    return values

def clean_string(some_text):
    clean_text = some_text

    # delete any leading {bc}
    clean_text = re.sub("^{bc}", "", clean_text)
    # any internal {bc} gets replaced with :
    clean_text = re.sub("{bc}", ": ", clean_text)

    # remove link markings begin
    clean_text = re.sub("{sx\|", "", clean_text)
    # remove link markings end
    clean_text = re.sub("\|\|\.*}", "", clean_text)

    # remove italics markings - TODO replace w/html
    clean_text = re.sub("{it}", "", clean_text)
    clean_text = re.sub("{/it}", "", clean_text)

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



# API_URL = 'https://www.dictionaryapi.com/api/v3/references/sd3/json/' + word + '?key=' + dict_key
# r = requests.get(url)

# json = r.json()
# for definition in json:
#     print(definition["shortdef"])


# Opening JSON file
f = open('definition.json')

# returns JSON object as a dictionary
data = json.load(f)

headwords = ["above", "alliteration", "boat", "career", "colored", "feline", "haze", "heart",
             "master", "Mauretania", "mistress", "plantation", "quotes", "savage",
             "shop", "slave", "superintendent",  "tedious"]

# may want to exclude offensive words? not sure if there are any offensive words in intermediate dictionary

for definition_entry in data:
    # clean any syllable markers (asterisk) from headword
    # remove anything inside curly brackets?
    #   example is N-allylnormorphine "hw":"{bit}N{\/bit}-al*lyl*nor*mor*phine"
    clean_headword = ""
    if definition_entry["hwi"]["hw"]:
        clean_headword = definition_entry["hwi"]["hw"].replace("*", "")
    else:
        print("NO HEADWORD FOUND")

    # change this to match with currently selected word
    # need additional cleaning? compare only lower case?
    if clean_headword in headwords:
        print('HEAD WORD = ' + clean_headword)

        if definition_entry["meta"]["stems"]:
            print('STEMS or ALTERNATE FORMS =', definition_entry["meta"]["stems"])

        if 'fl' in definition_entry:
            print('POS = ' + definition_entry["fl"])

        # COMMENTING OUT FOR NOW - URLS ARE DENIED
        # check for artwork
        # returns the art and a caption - no alt text
        # https://www.merriam-webster.com/assets/mw/static/art/dict/heart.gif
        # is there an assumption that there is only one image??
        # MW_ART_URL = 'https://www.merriam-webster.com/assets/mw/static/art/dict/'
        #
        # if 'art' in definition_entry:
        #     if definition_entry["art"]["artid"]:
        #         art_url = MW_ART_URL + definition_entry['art']['artid']
        #         print('ART FILE URL: ', art_url)
        #     if definition_entry['art']['artid']:
        #         art_caption = clean_string(definition_entry['art']['capt'])
        #         # remove any sup in caption - TODO not sure about numbers - LDM
        #         art_caption = re.sub("{sup}.*{/sup}", "", art_caption)
        #         print('ART CAPTION: ', art_caption)



#print('short definition = ', definition["shortdef"])

        print('DEFINITIONS')
        # extract a list of meanings with examples
        json_dt = json_extract(definition_entry, 'dt')
        print(json_dt);

        #print("UNIQUE Definitions for this POS = ", len(json_dt))
        for def_content in json_dt:

            clean_def = ""

            # Loop through the def_content: a list of name/value string pairs
            for def_instance in def_content:
                #print(def_instance)
                if len(def_instance) > 1 and def_instance[1] is not None:
                    # if this is a text check to see if there are any other parts to concat
                    if def_instance[0] == 'text':
                        clean_def = clean_def + clean_string(def_instance[1])
                    # if this is a vis (example) then parse and clean the list of examples
                    elif def_instance[0] == 'vis':
                        #print("FOUND EXAMPLES: ", def_instance[1])
                        examples = extract_examples(def_instance[1])
                        print("CLEANED EXAMPLES = ", examples)
                    # if this is an uns (unused) definition - discard
                    elif def_instance[0] == 'uns':
                        print("FOUND uns: ", def_instance[1])
                    # if this is a g then concat with the text
                    elif def_instance[0] == 'g':
                        clean_def = clean_def + def_instance[1]
                    # if this is another tag not accounted for - print to log file
                    else:
                        print("DEFINITION TYPE NOT FOUND = ", def_instance)
            if clean_def != "":
                print("CLEANED DEF: ", clean_def)

        print()
        print()

f.close()



