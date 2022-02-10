import wordfreq as wf


def sort_words_by_frequency(words, lang):
    """
    Sort the given list of words so that the lowest-frequency words are first.
    Zero-frequency words, however, are at the end of the list.
    :param words: iterable of words.
    :param lang: language code.  Only 'en' for English is currently supported.
    :return: sorted list of words.
    """
    # Words that return '0' for frequency (aka non-words) should go to the end of the list,
    # so give them a large sort key.
    def sort_key(word):
        freq = wf.word_frequency(word, lang)
        if freq > 0:
            return freq
        else:
            return 1

    word_list = [[w, sort_key(w)] for w in words]
    word_list.sort(key=lambda p: p[1])
    return [p[0] for p in word_list]
