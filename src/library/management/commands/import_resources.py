import json
import logging
import shutil
import traceback
from distutils import dir_util
from pathlib import Path
from zipfile import BadZipFile

from django.core.management.base import BaseCommand, CommandError

from library.models import EducatorResourceCategory, Book
from library.parsing import update_resource_from_epub_file, scan_book

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import or update items into the application for display on the Resources page. ' \
           'Requires an argument which is a JSON file listing information about the resources to be imported.'
    label = 'file'

    def add_arguments(self, parser):
        parser.add_argument('args', metavar=self.label, nargs='+')

    def handle(self, *labels, **options):
        self.check_args(*labels)
        resource_listing = Path(labels[0])
        if resource_listing.exists():
            dir = resource_listing.parent
            # Read JSON resource_file
            with open(resource_listing, 'r', encoding='utf-8') as resource_file:
                logger.debug("Reading resource_file %s", resource_file.name)
                resourcedata = json.load(resource_file)
                # Loop through outer list (categories)
                for seq, catinfo in enumerate(resourcedata):
                    cat, created = EducatorResourceCategory.objects.get_or_create(sort_order=seq)
                    resource_count = len(cat.resources.all())
                    cat.name = catinfo['name']
                    cat.save()
                    # Loop through inner list (resources for this category)
                    for item in catinfo['resources']:
                        # This will either update an existing Book, or add a new one. Returns the Book and a boolean.
                        resource: Book
                        resource, added = self.import_resource(identifier=item['identifier'], cat=cat, seq=resource_count,
                                         tags=item['tags'], path=dir.joinpath(item['file']))
                        if added:
                            resource_count += 1
                        if 'glossary' in item:
                            gloss_file = dir.joinpath(item['glossary'])
                            if gloss_file.exists():
                                shutil.copy(gloss_file, resource.glossary_storage)
                            else:
                                raise CommandError('Glossary file \'%s\' not found' % gloss_file)
                        if 'glossimages' in item:
                            image_dir = dir.joinpath(item['glossimages'])
                            if image_dir.exists():
                                dir_util.copy_tree(image_dir, resource.glossimages_storage)
                            else:
                                raise CommandError('Glossary image directory \'%s\' not found' % image_dir)

        else:
            raise CommandError('File \'%s\' not found' % resource_listing)

    def check_args(self, *labels):
        if len(labels) != 1:
            raise CommandError('A single file argument is required')

    def import_resource(self, identifier:str, cat:EducatorResourceCategory, seq:int, tags, path:Path):
        # If the identifier already exists, we just update it. Otherwise we add a new one.
        resource, created = Book.objects.get_or_create(resource_identifier=identifier)
        resource.resource_tags = json.dumps(tags)
        if created:
            resource.resource_sort_order = seq
            resource.resource_category = cat
            resource.featured = (seq == 0)
        resource.save()
        logger.debug('Importing %s from %s%s', identifier, path, ' (NEW)' if created else '')
        try:
            update_resource_from_epub_file(file=path, resource=resource)
            scan_book(resource)
            return resource, created
        except BadZipFile:
            raise CommandError('Not an EPUB file: %s' % path)
        except Exception as err:
            traceback.print_exc()
            raise CommandError('Error in %s: %s' % (path, err))
