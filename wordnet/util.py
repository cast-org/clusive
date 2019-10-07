from nltk.corpus import wordnet


def lookup(word):
    synsets = wordnet.synsets(word)
    if synsets:
        return {'headword': word,
                'meanings':
                    [{'pos': s.pos(),
                      'definition': s.definition(),
                      'synonyms': [lem.name() for lem in s.lemmas()],
                      'examples': [e for e in s.examples() if word in e],
                      } for s in synsets]
                }
    else:
        return None
