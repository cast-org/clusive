import logging
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import all books from a directory tree into the public library.\n' \
           'The given directory should have one subdirectory per book.\n' \
           'Each of those directories should have one or more EPUB files ' \
           'for the alternate versions, and may also contain ' \
           'a glossary.json file and directory of images, ' \
           'which will be attached to the book.'
    label = 'directory'

    def add_arguments(self, parser):
        parser.add_argument('args', metavar=self.label, action='append')

    def handle(self, *args, **options):
        for arg in args:
            path = Path(arg)
            if not (path.exists() and path.is_dir()):
                raise CommandError('Argument is not a directory')
            for subdir in path.iterdir():
                self.import_from_dir(subdir)

    def import_from_dir(self, subdir : Path):
        args = []
        for file in subdir.iterdir():
            args.append(file.absolute())
        call_command('import', *args)
