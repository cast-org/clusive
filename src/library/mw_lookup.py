import string

import requests
import json
import re

def json_extract(obj, key):
    # Recursively fetch values from nested JSON.
    arr = []

    def extract(obj, arr, key):
        # Recursively search for values of key in JSON tree.
        #print('FINDING VALUES for key =' + key)
        if isinstance(obj, dict):
            for k, v in obj.items():
                #print ('KEY = ' + k )
                if k == key:
                    #print ('FOUND A DT MATCH')
                    arr.append(v)
                elif isinstance(v, (dict, list)):
                    extract(v, arr, key)
                #elif k == key:
                #    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    values = extract(obj, arr, key)
    return values


# url = 'https://www.dictionaryapi.com/api/v3/references/sd3/json/' + word + '?key=' + dict_key
# r = requests.get(url)

# json = r.json()
# for definition in json:
#     print(definition["shortdef"])


# Opening JSON file
f = open('definition.json')

# returns JSON object as
# a dictionary
data = json.load(f)
#print("the length of the json = ", len(data))

headwords = ["above", "alliteration", "boat", "career", "colored", "feline", "haze", "heart",
             "master", "Mauretania", "mistress", "plantation", "quotes", "savage",
             "shop", "slave", "superintendent",  "tedious"]

# may want to exclude offensive words? not sure if there are any offensive words in intermediate dictionary

for definition in data:
    # clean any syllable markers (asterisk) from headword
    # remove anything inside curly brackets?
    #   example is N-allylnormorphine "hw":"{bit}N{\/bit}-al*lyl*nor*mor*phine"
    clean_headword = definition["hwi"]["hw"].replace("*","")

    # change this to match with currently selected word
    # need additional cleaning? compare only lower case?
    if clean_headword in headwords:
        print('HEAD WORD = ' + (definition["hwi"]["hw"]).replace("*",""))

        if definition["meta"]["stems"]:
            print('STEMS or ALTERNATE FORMS =', definition["meta"]["stems"])

        if 'fl' in definition:
            print('POS = ' + definition["fl"])

        # check for artwork
        # returns the art and a caption - no alt text
        # https://www.merriam-webster.com/assets/mw/static/art/dict/heart.gif
        # is there an assumption that there is only one image??
        if 'art' in definition:
            if definition["art"]["artid"]:
                print('ART FILE: ', definition['art']['artid'])
            if definition['art']['artid']:
                print('ART CAPTION: ', definition['art']['capt'])

        #print('short definition = ', definition["shortdef"])

        print('DEFINITIONS')
        json_dt = json_extract(definition, 'dt')
        #print(type(json_dt))
        #print(json_dt)
        #print("count of json_dt ", len(json_dt))

        for def_content in json_dt:
            print("DT OBJECT:", def_content)
            #print("count of def_content = ", len(def_content))
            # some content needs to be processed before looping through
            # e.g., 'g' needs to be concat into a single string
            #   sx should also be process - though not sure how
            # loop through the content
            for segments in def_content:
                #print("SEGMENTS = ", segments)
                index = 0
                for segment in segments:
                    #print("SEGMENT = ", segment)
                    #print(type(segment))
                    #print(segment[0:5])
                    if segment == 'text':
                        if segment[index + 1]:
                            print("DEFINITION: ", segments[index+1])
                    elif segment == 'vis':
                        if segment[index + 1]:
                            print("EXAMPLES = ", segments[index+1])
                    index +=1
            print("--")

        #vis = json.load(def_content)
            #vis = json_extract(def_content, 'vis')
            #print("vis = ", vis)

        # this does not work because the examples are no longer tied to the definition
        #temp_vis = json.dumps(json_extract(json_dt, 't'))
        #print(type(temp_vis))
        ##print(temp_vis)

        print()
        print()

# Closing file
f.close()



