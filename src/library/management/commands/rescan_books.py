import logging

from django.core.management.base import BaseCommand

from library.parsing import scan_all_books

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Rebuild automatically-constructed metadata of all books. ' \
           'Specifically: word lists, word/picture counts, reading levels, and subjects.' \
           'This is necessary only when new metadata fields are added, ' \
           'or the methods of calculating them are changed.'

    def handle(self, *args, **options):
        scan_all_books()
