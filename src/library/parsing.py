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


def unpack_epub_file(clusive_user, file):
    """
    Process an uploaded EPUB file, returns BookVersion

    This method will:
     * unzip the file into the user media area
     * find metadata
     * create a manifest
     * make a database record
    If there are any errors (such as a non-EPUB file), an exception will be raised.
    """
    with open(file, 'rb') as f, dawn.open(f) as upload:
        logger.debug('Upload EPUB%s: %s', upload.version, str(upload))
        manifest = make_manifest(upload)
        title = get_metadata_item(upload, 'titles') or 'Untitled'
        author = get_metadata_item(upload, 'creators') or 'Unknown'
        description = get_metadata_item(upload, 'description') or 'No description'
        cover = adjust_href(upload, upload.cover.href) if upload.cover else None
        book = Book(owner=clusive_user,
                    title=title,
                    author=author,
                    description=description,
                    cover=cover)
        book.save()
        bv = BookVersion(book=book, sortOrder=0)
        bv.save()
        dir = default_storage.path(bv.path)
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
