import logging
import os
import shutil
from distutils import dir_util
from pathlib import Path
from zipfile import BadZipFile

from django.core.management.base import BaseCommand, CommandError

from glossary.util import test_glossary_file
from library.parsing import unpack_epub_file, scan_book, BookNotUnique, BookMismatch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import files into the application that together become a public-library book. ' \
           'All EPUB files given on the command-line are considered to be' \
           'alternate versions of the same book. ' \
           'A glossary.json file and directory of images may also be listed, ' \
           'and will be attached to the book.\n\n' \
           'Note, if a public-library book with the same title already exists, it will not be imported.'
    label = 'file'

    copy_files = []
    book = None
    version = 0
    found_new_content = False

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
        if self.found_new_content:
            # Update word lists
            scan_book(self.book)
        else:
            logger.debug('No new content, skipping scan')

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
                    raise CommandError('Do not know how to import file: %s' % label)
            else:
                raise CommandError('File not found: %s' % label)
        if epubs == 0:
            raise CommandError('No .epub files provided, cannot import.')
        if directories > 1:
            raise CommandError('At most one directory (of glossary images) should be included.')
        if glossary > 1:
            raise CommandError('At most one JSON glossary file should be included.')
        if directories > glossary:
            raise CommandError('Directory given without a corresponding glossary JSON file.')

    def looks_like_an_epub(self, label):
        return label.lower().endswith(('.epub', '.epub3'))

    def looks_like_a_glossary(self, label):
        return label.lower().endswith('.json')

    def looks_like_glossary_image_directory(self, label):
        file = Path(label)
        return file.is_dir()

    def handle_epub(self, label: str):
        try:
            (bv, changed) = unpack_epub_file(None, label, self.book, self.version)
            if changed:
                self.found_new_content = True
            if bv and not self.book:
                self.book = bv.book
            self.version += 1
        except FileNotFoundError:
            raise CommandError('File not found')
        except BadZipFile:
            raise CommandError('Not an EPUB file')
        except BookMismatch:
            raise CommandError('Mismatched titles, stopping import')

    def handle_copy(self, label: str):
        if self.looks_like_a_glossary(label):
            shutil.copy(label, os.path.join(self.book.storage_dir, 'glossary.json'))
        elif self.looks_like_glossary_image_directory(label):
            glosspath = os.path.join(self.book.storage_dir, 'glossimages')
            dir_util.copy_tree(label, glosspath)
            logger.debug('Copied glossary images to %s', glosspath)
