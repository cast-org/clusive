from clusive_project import settings


def lookup(word: str):
    """
    Look up a word in the Merriam-Webster dictionary API and return a definition structure.
    If the word is not found, return None.
    :param word: base form of the word to look up
    :return: python object in Clusive's standard glossary format.
    """
    api_key = settings.MERRIAM_WEBSTER_API_KEY
    if not api_key:
        return None

    # For testing purposes, this stub function will "find" a definition for any word that starts with 'M' or 'W'
    if word.startswith('m') or word.startswith('w'):
        # TODO: actually look up the word and return the meanings, rather than this example one.
        return {
            'headword': word,
            'meanings':
                [
                    {'pos': 'adverb',
                     'definition': 'in or to a higher place; overhead',},
                    {'pos': 'adverb',
                     'definition': 'higher on the same or a preceding page'},
                    {'pos': 'preposition',
                     'definition': 'in or to a higher place than; over'},
                    {'pos': 'preposition',
                     'definition': 'superior to',
                     'examples': ['a captain is above a lieutenant', 'above criticism'],}
                ]
        }
    else:
        return None
