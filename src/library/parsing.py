import json
import logging
import os
import posixpath
from html.parser import HTMLParser
from zipfile import ZipFile

import dawn
from dawn.epub import Epub
from django.core.files.storage import default_storage
from nltk import RegexpTokenizer

from glossary.util import base_form
from library.models import Book, BookVersion

logger = logging.getLogger(__name__)


class BookMismatch(Exception):
    pass


def unpack_epub_file(clusive_user, file, book=None, version=0):
    """
    Process an uploaded EPUB file, returns BookVersion.

    If book and version arguments are given, it is created as that version.
    Otherwise, a new Book is created and this is the first version.

    This method will:
     * unzip the file into the user media area
     * find metadata
     * create a manifest
     * make a database record

    It does NOT look for glossary words or parse the text content for vocabulary lists,
    call scan_book for that.

    If there are any errors (such as a non-EPUB file), an exception will be raised.
    """
    with open(file, 'rb') as f, dawn.open(f) as upload:
        logger.debug('Unpacking EPUB%s: %s', upload.version, str(upload))
        manifest = make_manifest(upload)
        title = get_metadata_item(upload, 'titles') or 'Untitled'
        author = get_metadata_item(upload, 'creators') or 'Unknown'
        description = get_metadata_item(upload, 'description') or 'No description'
        cover = adjust_href(upload, upload.cover.href) if upload.cover else None

        if book:
            if book.title != title:
                raise BookMismatch('Does not appear to be a version of the same book, titles differ.')
        else:
            book = Book(owner=clusive_user,
                        title=title,
                        author=author,
                        description=description,
                        cover=cover)
            book.save()
        bv = BookVersion(book=book, sortOrder=version)
        bv.save()
        dir = bv.storage_dir
        os.makedirs(dir)
        with ZipFile(file) as zf:
            zf.extractall(path=dir)
        with open(os.path.join(dir, 'manifest.json'), 'w') as mf:
            mf.write(json.dumps(manifest, indent=4))
        logger.debug("Unpacked epub into %s", dir)
        return bv


def get_metadata_item(book, name):
    item = book.meta.get(name)
    if item:
        if isinstance(item, list):
            if len(item)>0:
                return item[0]
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
        if v.data.get('file=as'):
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
    versions = b.versions.all()
    for bv in versions:
        # Read the book manifest
        if os.path.exists(bv.manifest_file):
            with open(bv.manifest_file, 'r') as file:
                manifest = json.load(file)
                # I think we don't want to do this, if metadata may be editable through the web
                # but not quite ready to delete it outright.
                # b.title = find_title(manifest)
                # b.description = find_description(manifest)
                # cover_link = find_cover(manifest)
                # b.cover = str(bv.sortOrder) + "/" + cover_link if cover_link else None
                # b.save()
                bv.all_word_list = find_all_words(bv.storage_dir, manifest)
                logger.debug('%s: parsed %d words', bv, len(bv.all_word_list))
                bv.glossary_word_list = find_glossary_words(b.storage_dir, bv.all_word_list)
                bv.save()
        else:
            logger.error("Book directory had no manifest: %s", bv.manifest_file)
    # After all versions are read, determine new words added in each version.
    if len(versions) > 1:
        for bv in versions:
            if bv.sortOrder > 0:
                bv.new_word_list = list(set(bv.all_word_list) - set(versions[bv.sortOrder - 1].all_word_list))
                bv.save()


def find_title(manifest):
    title = manifest['metadata'].get('title')
    if not title:
        title = manifest['metadata'].get('headline')
    return title


def find_description(manifest):
    return manifest['metadata'].get('description') or ""


def find_cover(manifest):
    for item in manifest['resources']:
        if item.get('rel') == 'cover':
            return item.get('href')
    return None


def find_glossary_words(book_dir, all_words):
    glossaryfile = os.path.join(book_dir, 'glossary.json')
    if os.path.exists(glossaryfile):
        with open(glossaryfile, 'r', encoding='utf-8') as file:
            glossary = json.load(file)
            words = [base_form(e['headword']) for e in glossary]
            this_version_words = sorted(set(words).intersection(all_words))
            return this_version_words
    else:
        return []


def find_all_words(version_dir, manifest):
    # Look up content files in manifest
    # For each one, gather words
    # Format word set as JSON and return it for storage in database
    te = TextExtractor()
    for file_info in manifest['readingOrder']:
        te.feed_file(os.path.join(version_dir, file_info['href']))
    return sorted(te.get_word_set())


class TextExtractor(HTMLParser):
    element_stack = []
    text = ''
    file = None

    ignored_elements = {'head', 'script'}
    delimiter = ' '

    def feed_file(self, file):
        self.file = file
        with open(file, 'r', encoding='utf-8') as html:
            for line in html:
                self.feed(line)
        self.file = None

    def get_word_set(self):
        self.close()
        token_list = RegexpTokenizer(r'\w+').tokenize(self.text)
        token_set = set([base for base in
                         (base_form(w) for w in token_list if w.isalpha())
                         if base is not None])
        return token_set

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
