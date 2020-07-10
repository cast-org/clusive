import logging
import os
import shutil
from pathlib import Path
from zipfile import BadZipFile

from django.core.management.base import BaseCommand

from glossary.util import test_glossary_file
from library.parsing import unpack_epub_file, scan_book

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import files into the application that together become a public-library book. ' \
           'All EPUB files given on the command-line are considered to be' \
           'alternate versions of the same book. ' \
           'A glossary.json file and directory of images may also be listed, ' \
           'and will be attached to the book.'
    label = 'file'

    copy_files = []
    book = None
    version = 0

    def add_arguments(self, parser):
        parser.add_argument('args', metavar=self.label, nargs='+')

    def handle(self, *labels, **options):
        self.check_args(*labels)
        # Unpack EPUB files first
        for label in [l for l in labels if self.looks_like_an_epub(l)]:
            self.handle_epub(label)
        # Then copy in the other items
        for label in [l for l in labels if not self.looks_like_an_epub(l)]:
            self.handle_copy(label)
        # Update word lists
        scan_book(self.book)

    def check_args(self, *labels):
        epubs = 0
        directories = 0
        glossary = 0
        for label in labels:
            file = Path(label)
            if file.exists():
                if self.looks_like_glossary_image_directory(label):
                    directories += 1
                elif self.looks_like_a_glossary(label):
                    glossary += 1
                    glossary_errors = test_glossary_file(file)
                    if glossary_errors:
                        self.stderr.write('Glossary errors: %s' % glossary_errors)
                        exit(1)
                elif self.looks_like_an_epub(label):
                    epubs += 1
                else:
                    self.stderr.write('Do not know how to import file: %s' % label)
                    exit(1)
            else:
                self.stderr.write('File not found: %s' % label)
        if epubs == 0:
            self.stderr.write('No .epub files provided, cannot import.')
            exit(1)
        if directories > 1:
            self.stderr.write('At most one directory (of glossary images) should be included.')
            exit(1)
        if glossary > 1:
            self.stderr.write('At most one JSON glossary file should be included.')
            exit(1)
        if directories > glossary:
            self.stderr.write('Directory given without a corresponding glossary JSON file.')
            exit(1)

    def looks_like_an_epub(self, label):
        return label.lower().endswith(('.epub', '.epub3'))

    def looks_like_a_glossary(self, label):
        return label.lower().endswith('.json')

    def looks_like_glossary_image_directory(self, label):
        file = Path(label)
        return file.is_dir()

    def handle_epub(self, label: str):
        try:
            bv = unpack_epub_file(None, label, self.book, self.version)
            if not self.book:
                self.book = bv.book
            self.version += 1
        except FileNotFoundError:
            self.stderr.write('File not found')
            exit(1)
        except BadZipFile:
            self.stderr.write('Not an EPUB file')
            exit(1)

    def handle_copy(self, label: str):
        if self.looks_like_a_glossary(label):
            shutil.copy(label, os.path.join(self.book.storage_dir, 'glossary.json'))
        elif self.looks_like_glossary_image_directory(label):
            shutil.copytree(label, os.path.join(self.book.storage_dir, 'glossimages'))
