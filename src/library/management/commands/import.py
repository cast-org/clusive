import logging
import sys
from zipfile import BadZipFile

from django.core.management.base import BaseCommand, CommandError, LabelCommand
from django.contrib.auth.models import User

from library.parsing import unpack_epub_file
from roster.models import Site, Period, ClusiveUser

logger = logging.getLogger(__name__)

class Command(LabelCommand):
    help = 'Import an EPUB file into the application as a public-library book'

    def handle_label(self, label, **options):
        try:
            unpack_epub_file(None, label)
        except FileNotFoundError:
            self.stderr.write('File not found')
        except BadZipFile:
            self.stderr.write('Not an EPUB file')
