import logging
import sys
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from library.parsing import BookNotUnique

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import all books from a directory tree into the public library.\n' \
           'The given directory should have one subdirectory per book.\n' \
           'Each of those directories should have one or more EPUB files ' \
           'for the alternate versions, and may also contain ' \
           'a glossary.json file and directory of images, ' \
           'which will be attached to the book.\n\n' \
           'If a public-library book with the same name already exists, the directory will be skipped.'
    label = 'directory'

    def add_arguments(self, parser):
        parser.add_argument('args', metavar=self.label, action='append')

    def handle(self, *args, **options):
        for arg in args:
            path = Path(arg)
            if not (path.exists() and path.is_dir()):
                raise CommandError('Argument is not a directory')
            for subdir in path.iterdir():
                if not subdir.name.startswith('.') and subdir.is_dir():
                    self.import_from_dir(subdir)
                else:
                    logger.warning('Ignoring non-directory %s' % subdir)

    def import_from_dir(self, subdir : Path):
        args = []
        for file in subdir.iterdir():
            if not file.name.startswith('.'):
                args.append(file.absolute())
        # We make the assumption that version EPUBs are in lexicographic order by their difficulty.
        # Eg penguins-0.epub, penguins-1.epub, penguins-2.epub would be fine.
        args.sort()
        try:
            call_command('import', *args)
        except BookNotUnique as e:
            # Skip this import, but we catch the exception so that other imports can proceed.
            self.stderr.write(str(e))
