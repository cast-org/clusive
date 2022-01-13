import json
import logging
import os
import posixpath
import shutil
import requests
from html.parser import HTMLParser
from os.path import basename
from tempfile import mkstemp
from urllib.parse import urlparse
from zipfile import ZipFile

import dawn
import pypandoc
import wordfreq as wf
from dawn.epub import Epub
from django.utils import timezone
from nltk import RegexpTokenizer

from glossary.util import base_form
from library.models import Book, BookVersion, Subject

logger = logging.getLogger(__name__)


class BookMismatch(Exception):
    pass


class BookNotUnique(Exception):
    pass


class BookMalformed(Exception):
    pass


def convert_and_unpack_docx_file(clusive_user, file):
    """
    Process an uploaded Word (docx) file. Converts to EPUB and then calls unpack_epub_file.
    :param clusive_user: user that will own the resulting Book.
    :param file: File, which should be a .docx.
    :return: a new BookVersion
    """
    fd, tempfile = mkstemp()
    output = pypandoc.convert_file(file, 'epub', outputfile=tempfile)
    if output:
        raise RuntimeError(output)
    return unpack_epub_file(clusive_user, tempfile, omit_filename='title_page.xhtml')

import pdb
def unpack_epub_file(clusive_user, file, book=None, sort_order=0, omit_filename=None, bookshare_metadata=None):
    """
    Process an uploaded EPUB file, returns BookVersion.

    The book will be owned by the given ClusiveUser. If that argument is None, it will be
    created as a public library book.

    If book and sort_order arguments are given, they will be used to locate an existing Book and
    possibly-existing BookVersion objects. For public library books, the title is used to
    look for a matching Book. If there is no matching Book or BookVersion, they will be created.
    If a matching BookVersion already exists it will be overwritten only if
    the modification date in the EPUB metadata is newer.

    If bookshare_metadata is provided, it will be used to fill in metadata fields and record the bookshare ID.

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
        manifest = make_manifest(upload, omit_filename)
        title = get_metadata_item(upload, 'titles') or ''
        author = get_metadata_item(upload, 'creators') or ''
        sort_author = ''
        description = get_metadata_item(upload, 'description') or ''
        language = get_metadata_item(upload, 'language') or ''
        tempcover_info = None

        if bookshare_metadata:
            # Bookshare EPUBs don't seem to have much metadata embedded, but the API gives us some we can add.
            logging.debug('Bookshare metadata was provided: %s', bookshare_metadata)
            bookshare_id = bookshare_metadata['bookshareId']
            if title == '':
                logger.debug('Title was blank, set to value from bookshare_metadata')
                title = bookshare_metadata.get('title', '')
            if author == '':
                logger.debug('Author was blank, set to value from bookshare_metadata')
                authors = []
                sort_authors = []
                for contributor in bookshare_metadata.get('contributors', []):
                    if contributor['type'] == 'author':
                        authors.append(contributor['name']['displayName'])
                        sort_authors.append(contributor['name']['indexName'])
                if len(authors) > 2:
                    author = ', '.join(authors[:-1]) + ', and ' + authors[-1]
                    sort_author = ', '.join(sort_authors[:-1]) + ', and ' + sort_authors[-1]
                else:
                    author = ' and '.join(authors)
                    sort_author = ' and '.join(sort_authors)
            if description == '':
                logger.debug('Description was blank, set to value from bookshare_metadata')
                description = bookshare_metadata.get('synopsis', '')[:500]
            # TODO language? { 'languages': ['eng'] }
            # TODO subjects from eg { 'categories': [{'name': 'History', ...}...] }
            if upload.cover is None:
                for link in bookshare_metadata.get('links', []):
                    if link['rel'] == 'coverimage':
                        tempcover_info = download_and_save_cover(link['href'], bookshare_id)
                        break
        else:
            bookshare_id = None

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
        elif tempcover_info is not None:
            cover = tempcover_info['filename']
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
                        sort_author=sort_author,
                        description=description,
                        cover=cover,
                        bookshare_id=bookshare_id)
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

        # If the cover image was retrieved and stored in a tmp file, move it to
        # the new EPUB storage directory.
        if tempcover_info and book.cover_storage:
            shutil.copyfile(tempcover_info['tempfile'], book.cover_storage)

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


def make_manifest(epub: Epub, omit_filename: str):
    """
    Create Readium manifest based on the given EPUB.
    :param epub: EPUB file as parsed by Dawn.
    :param omit_filename: If supplied, any file in the spine with the given name
        will be omitted from the reading order in the manifest.
    :return: object that can be written as JSON to form the manifest file.
    """
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
        if not (omit_filename and s.href.endswith('/'+omit_filename)):
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
    set_subjects(b)
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
                logger.debug('Setting sort title to the title: %s', title)
                sort_title = title
            book.sort_title = sort_title or ''

            author_list = manifest['metadata'].get('author')
            if author_list:
                author = author_list[0].get('name')
                sort_author = author_list[0].get('sortAs')
                logger.debug('Sort author: %s', sort_author)
                if not sort_author:
                    # TODO: maybe should make some default assumptions, First Last -> Last first
                    logger.debug('Setting sort author to the author: %s', author )
                    sort_author = author
                book.sort_author = sort_author or ''

def set_subjects(book):
    # Get all valid subjects
    valid_subjects = Subject.objects.all()

    # Read the subject array out of the first version of the book
    bv = book.versions.all()[0]
    if os.path.exists(bv.manifest_file):
        with open(bv.manifest_file, 'r') as file:
            manifest = json.load(file)

            # clear any current subjects
            if book.subjects.count() > 0:
                logger.debug('Removing these subjects from the book: %s', book.subjects.all())
                book.subjects.clear()

            #  make a list of subjects from the manifest
            bs = manifest['metadata'].get('subject')

            #  if bs is a string then there is only 1 subject
            book_subjects = []
            if isinstance(bs, str) or bs == None:
                book_subjects.append(bs)
            else:
                book_subjects.extend(bs)
            logger.debug('These are the book subjects to add: %s', book_subjects)

            # Loop through subjects array checking for valid subjects only
            if book_subjects:
                for s in book_subjects:
                    if s is not None:
                        if valid_subjects.filter(subject__iexact=s).exists():
                            logger.debug('Adding subject relationship for: %s', s)
                            book.subjects.add(valid_subjects.filter(subject__iexact=s).first())
                        else:
                            logger.debug('Subject is not in the subject table: %s', s)
    else:
        logger.error("Book directory had no manifest: %s", bv.manifest_file)



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

def download_and_save_cover(href, book_id):
    """
    Download and save the cover image to a tmp file, and return information
    about that file: the intended cover filename, and the full path to the tmp
    file.  Return None if if something goes wrong fails.
    """
    resp = requests.request('GET', href)
    if resp.status_code == 200:
        src_url = urlparse(href)
        filename_from_url = os.path.basename(src_url.path)
        file_ext = os.path.splitext(filename_from_url)
        cover_filename = 'cover' + str(book_id)
        fd, tempfile = mkstemp(suffix=file_ext[1], prefix=cover_filename)
        with os.fdopen(fd, 'wb') as f:
            f.write(resp.content)
            f.close()
        return {
            'filename': cover_filename + file_ext[1],
            'tempfile': tempfile,
        }
    else:
        return None

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
