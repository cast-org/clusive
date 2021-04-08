import json
import logging
import os
import posixpath
import shutil
from html.parser import HTMLParser
from os.path import basename
from zipfile import ZipFile

import dawn
import wordfreq as wf
from dawn.epub import Epub
from django.utils import timezone
from nltk import RegexpTokenizer

from glossary.util import base_form
from library.models import Book, BookVersion

logger = logging.getLogger(__name__)


class BookMismatch(Exception):
    pass


class BookNotUnique(Exception):
    pass


class BookMalformed(Exception):
    pass


def unpack_epub_file(clusive_user, file, book=None, sort_order=0):
    """
    Process an uploaded EPUB file, returns BookVersion.

    The book will be owned by the given ClusiveUser. If that argument is None, it will be
    created as a public library book.

    If book and sort_order arguments are given, they will be used to locate an existing Book and
    possibly-existing BookVersion objects. For public library books, the title is used to
    look for a matching Book. If there is no matching Book or BookVersion, they will be created.
    If a matching BookVersion already exists it will be overwritten only if
    the modification date in the EPUB metadata is newer.

    This method will:
     * unzip the file into the user media area
     * find the most basic metadata
     * create the manifest.json
     * make a database record

    It does NOT look for glossary words or parse the text content for vocabulary lists,
    call scan_book for that.

    Returns a tuple (bv, changed) of the BookVersion and a boolean value which will
    be true if new book content was found.  If "changed" is False, the bv is an existing
    one that matches the given file and was not updated.

    If there are any errors (such as a non-EPUB file), an exception will be raised.
    """
    with open(file, 'rb') as f, dawn.open(f) as upload:
        manifest = make_manifest(upload)
        title = get_metadata_item(upload, 'titles') or ''
        author = get_metadata_item(upload, 'creators') or ''
        description = get_metadata_item(upload, 'description') or ''
        language = get_metadata_item(upload, 'language') or ''

        mod_date = upload.meta.get('dates').get('modification') or None
        # Date, if provided should be UTC according to spec.
        if mod_date:
            mod_date = timezone.make_aware(mod_date, timezone=timezone.utc)
        else:
            # Many EPUBs are missing this metadata, unfortunately.
            logger.warning('No mod date found in %s', file)
            mod_date = timezone.now()

        if upload.cover:
            cover = adjust_href(upload, upload.cover.href)
            # For cover path, need to prefix this path with the directory holding this version of the book.
            cover = os.path.join(str(sort_order), cover)
        else:
            cover = None

        # Find or create the BOOK.
        if book:
            # Was supplied as an arg... sanity check.
            if book.title != title:
                logger.warning('DB title: \'%s\', imported title: \'%s\'' % (repr(book.title), repr(title)))
                raise BookMismatch('Does not appear to be a version of the same book, titles differ.')
        else:
            if not clusive_user:
                # For public books, we require a title, and a book with the same title is assumed to be the same book.
                if not title:
                    raise BookMalformed('Malformed EPUB, no title found')
                book = Book.objects.filter(owner=None, title=title).first()
        if not book:
            # Make new Book
            book = Book(owner=clusive_user,
                        title=title,
                        author=author,
                        description=description,
                        cover=cover)
            book.save()
            logger.debug('Created new book for import: %s', book)

        # Find or create the BOOK VERSION
        book_version = BookVersion.objects.filter(book=book, sortOrder=sort_order).first()
        if book_version:
            logger.debug('Existing BV was found')
            if mod_date > book_version.mod_date:
                logger.info('Replacing older content of this book version')
                book_version.mod_date = mod_date
                # Also update metadata that's stored on the book, in case it's changed.
                book.author = author
                book.description = description
                book.cover = cover
                book.save()
            else:
                logger.warning('File %s not imported: already exists with same or newer date' % file)
                # Short circuit the import and just return the existing object.
                return book_version, False
        else:
            logger.debug('Creating new BV: book=%s, sortOrder=%d' % (book, sort_order))
            book_version = BookVersion(book=book, sortOrder=sort_order, mod_date=mod_date)

        book_version.filename = basename(file)
        if language:
            book_version.language = language
        book_version.save()

        # Unpack the EPUB file
        dir = book_version.storage_dir
        if os.path.isdir(dir):
            logger.debug('Erasing existing content in %s', dir)
            shutil.rmtree(dir)
        os.makedirs(dir)
        with ZipFile(file) as zf:
            zf.extractall(path=dir)
        with open(os.path.join(dir, 'manifest.json'), 'w') as mf:
            mf.write(json.dumps(manifest, indent=4))
        logger.debug("Unpacked epub into %s", dir)
        return book_version, True


def get_metadata_item(book, name):
    item = book.meta.get(name)
    if item:
        if isinstance(item, list):
            if len(item)>0:
                return str(item[0])
        else:
            return str(item)
    return None


def make_manifest(epub: Epub):
    data = {
            '@context': 'https://readium.org/webpub-manifest/context.jsonld',
            'metadata': {
                '@type': 'http://schema.org/Book',
            },
            "readingOrder": [],
            "resources": []
        }

    # METADATA
    for k, v in epub.meta.items():
        # logger.debug('Found metadata key: %s, val: %s' % (k, repr(v)))
        if v:
            metadata = data['metadata']
            if k == 'dates':
                metadata['modified'] = str(epub.meta.get('dates').get('modification'))
            elif k == 'titles':
                metadata['title'] = str(v[0].value)
                if v[0].data.get('file-as'):
                    metadata['sortAs'] = v[0].data.get('file-as')
            elif k == 'contributors':
                metadata['contributor'] = make_contributor(v)
            elif k == 'creators':
                metadata['author'] = make_contributor(v)
            elif k.endswith('s'):
                if len(v) > 1:
                    metadata[k[:-1]] = [str(x) for x in v]
                else:
                    metadata[k[:-1]] = str(v[0])
            else:
                metadata[k] = str(v)

    # READING ORDER
    ro = data['readingOrder']

    for s in epub.spine:
        ro.append({
            'href': adjust_href(epub, s.href),
            'type': s.mimetype
            # TODO properties.contains = ['svg']
        })

    # RESOURCES
    resources = data['resources']
    for k,v in epub.manifest.items():
        res = {
            'href': adjust_href(epub, v.href),
            'type': v.mimetype
        }
        if v is epub.cover:
            res['rel'] = 'cover'
        resources.append(res)

    # TOC
    data['toc'] = [make_toc_item(epub, it) for it in epub.toc]

    return data


def adjust_href(epub, href):
    """Take href relative to OPF and make it relative to the EPUB root dir."""
    opfdir = posixpath.dirname(epub._opfpath)
    return posixpath.join(opfdir, href)


def make_contributor(val):
    result = []
    for v in val:
        item = {'name': str(v.value)}
        if v.data.get('role'):
            item['role'] = v.data.get('role')
        if v.data.get('file-as'):
            item['sortAs'] = v.data.get('file-as')
        result.append(item)
    return result


def make_toc_item(epub, it):
    res = {
        'href': adjust_href(epub, it.href),
        'title': it.title}
    if it.children:
        res['children'] = [make_toc_item(epub, c) for c in it.children]
    return res


def scan_all_books():
    """Go through all books and versions and update the database"""
    for book in Book.objects.all():
        scan_book(book)


def scan_book(b):
    """Looks through book manifest and text files and sets or updates database metadata."""
    glossary_words = find_glossary_words(b.storage_dir)
    versions = b.versions.all()
    for bv in versions:
        find_all_words(bv, glossary_words)
        count_pictures(bv)
    # After all versions are read, gather global metadata
    # Book word_count is the average of version word_counts.
    set_sort_fields(b)
    b.word_count = sum([v.word_count for v in versions])/len(versions)
    b.picture_count = sum([v.picture_count for v in versions])/len(versions)
    b.save()
    # determine new words added in each version.
    if len(versions) > 1:
        for bv in versions:
            if bv.sortOrder > 0:
                words = bv.all_word_list
                prev_words = versions[bv.sortOrder - 1].all_word_list
                bv.new_word_list = [w for w in words if not w in prev_words]
                bv.save()


def set_sort_fields(book):
    # Read the title and sort_title out of the first version. THey should all be the same.
    bv = book.versions.all()[0]
    if os.path.exists(bv.manifest_file):
        with open(bv.manifest_file, 'r') as file:
            manifest = json.load(file)
            title = manifest['metadata'].get('title')
            sort_title = manifest['metadata'].get('sortAs')
            logger.debug('Sort title: %s', sort_title)
            if not sort_title:
                # TODO: should make some simple default assumptions, like removing 'The'/'A'
                sort_title = title
            book.sort_title = sort_title

            author_list = manifest['metadata'].get('author')
            if author_list:
                author = author_list[0].get('name')
                sort_author = author_list[0].get('sortAs')
                if not sort_author:
                    # TODO: maybe should make some default assumptions, First Last -> Last first
                    sort_author = author
                book.sort_author = sort_author


def find_glossary_words(book_dir):
    glossaryfile = os.path.join(book_dir, 'glossary.json')
    if os.path.exists(glossaryfile):
        with open(glossaryfile, 'r', encoding='utf-8') as file:
            glossary = json.load(file)
            words = [base_form(e['headword']) for e in glossary]
            return words
    else:
        return []


def count_pictures(bv):
    if os.path.exists(bv.manifest_file):
        with open(bv.manifest_file, 'r') as file:
            manifest = json.load(file)
            pictures = 0
            for item in manifest['resources']:
                logger.debug('Manifest item: %s', repr(item))
                if item['type'] and item['type'].startswith('image/'):
                    pictures += 1
            bv.picture_count = pictures
            bv.save()


def find_all_words(bv, glossary_words):
    # Read the book manifest
    if os.path.exists(bv.manifest_file):
        with open(bv.manifest_file, 'r') as file:
            te = TextExtractor()
            manifest = json.load(file)
            # Look up content files in manifest
            for file_info in manifest['readingOrder']:
                # For each one, gather words
                te.feed_file(os.path.join(bv.storage_dir, file_info['href']))
            found = te.get_word_lists(glossary_words)
            bv.all_word_list = found['all_words']
            bv.non_dict_word_list = found['non_dict_words']
            bv.glossary_word_list = found['glossary_words']
            bv.word_count = found['word_count']
            logger.debug('%s: parsed %d words; %d glossary words; %d dictionary words; %d non-dict words',
                         bv, bv.word_count,
                         len(bv.glossary_word_list), len(bv.all_word_list), len(bv.non_dict_word_list))
            bv.save()
    else:
        logger.error("Book directory had no manifest: %s", bv.manifest_file)


class TextExtractor(HTMLParser):
    element_stack = []
    text = ''
    file = None
    lang = 'en' # FIXME should really be language of book passed in.

    ignored_elements = {'head', 'script'}
    delimiter = ' '

    def feed_file(self, file):
        self.file = file
        with open(file, 'r', encoding='utf-8') as html:
            for line in html:
                self.feed(line)
        self.file = None

    def get_word_lists(self, glossary_words):
        self.close()
        tokens = RegexpTokenizer(r'\w+').tokenize(self.text)
        word_count = len(tokens)
        token_set = set(tokens)
        glossary_set = set()
        word_set = set()
        non_word_set = set()
        for t in token_set:
            if t.isalpha():
                if t.lower() in glossary_words:
                    # Found in glossary
                    glossary_set.add(t.lower())
                    word_set.add(t.lower())
                else:
                    base = base_form(t, return_word_if_not_found=False)
                    if base:
                        # Found in dictionary
                        if base in glossary_words:
                            # Base form also found in glossary
                            glossary_set.add(base)
                        word_set.add(base)
                    else:
                        # Neither in glossary, nor in dictionary
                        non_word_set.add(t.lower())
        # Append frequency of each word, sort by it, then remove the frequencies from return value
        word_list = [[w, self.sort_key(w)] for w in word_set]
        word_list.sort(key=lambda p: p[1])
        word_list = [p[0] for p in word_list]
        # Glossary and non-dictionary words are just sorted alphabetically.
        glossary_list = list(glossary_set)
        glossary_list.sort()
        non_word_list = list(non_word_set)
        non_word_list.sort()
        return {
            'glossary_words': glossary_list,
            'all_words': word_list,
            'non_dict_words': non_word_list,
            'word_count': word_count,
        }

    # We sort the hardest (low-frequency) words to the front of our list.
    # However, words that return '0' for frequency (aka non-words) should go to the end of the list,
    # so give them a large sort key.
    def sort_key(self, word):
        freq = wf.word_frequency(word, self.lang)
        if freq > 0:
            return freq
        else:
            return 1

    def extract(self, html):
        self.feed(html)
        self.close()
        return self.text

    def handle_starttag(self, tag, attrs):
        self.element_stack.insert(0, tag)

    def handle_endtag(self, tag):
        if not tag in self.element_stack:
            logger.warning("Warning: close tag for element that is not open: %s in %s; file=",
                        tag, self.element_stack, self.file)
            return
        index = self.element_stack.index(tag)
        if index > 0:
            logger.warning("Warning: improper nesting of end tag %s in %s; file=%s",
                        tag, self.element_stack, self.file)
        del self.element_stack[0:index+1]

    def handle_data(self, data):
        if len(self.ignored_elements.intersection(self.element_stack)) == 0:
            self.text += data + self.delimiter

    def error(self, message):
        logger.error(message)
