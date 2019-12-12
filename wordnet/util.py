from nltk.corpus import wordnet


pos_names = {
    wordnet.ADJ : "adjective",
    wordnet.ADJ_SAT: "adjective",
    wordnet.ADV: "adverb",
    wordnet.NOUN: "noun",
    wordnet.VERB: "verb"
}

def lookup(word):
    synsets = wordnet.synsets(word)
    if synsets:
        return {'headword': word,
                'meanings':
                    [{'pos': pos_names[s.pos()],
                      'definition': s.definition(),
                      'synonyms': [lem.name() for lem in s.lemmas()],
                      'examples': [e for e in s.examples() if word in e],
                      } for s in synsets]
                }
    else:
        return None
