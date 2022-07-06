import json
import logging
import traceback
from pathlib import Path
from zipfile import BadZipFile

from django.core.management.base import BaseCommand, CommandError

from library.models import EducatorResource, EducatorResourceCategory
from library.parsing import update_resource_from_epub_file

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import or update items into the application for display on the Resources page. ' \
           'Requires an argument which is a JSON file listing information about the resources'
    label = 'file'

    def add_arguments(self, parser):
        parser.add_argument('args', metavar=self.label, nargs='+')

    def handle(self, *labels, **options):
        self.check_args(*labels)
        resource_listing = Path(labels[0])
        if resource_listing.exists():
            # Read JSON resource_file
            with open(resource_listing, 'r', encoding='utf-8') as resource_file:
                logger.debug("Reading resource_file %s", resource_file.name)
                resourcedata = json.load(resource_file)
                # Remove all existing resources from categories so any old ones don't get in the way.
                for r in EducatorResource.objects.all():
                    r.category = None
                    r.sort_order = 0
                    r.save()
                # Loop through outer list (categories)
                for seq, catinfo in enumerate(resourcedata):
                    cat, created = EducatorResourceCategory.objects.get_or_create(sort_order=seq)
                    cat.name = catinfo['name']
                    cat.save()
                    # Loop through inner list (resources for this category)
                    for seq, item in enumerate(catinfo['resources']):
                        self.import_item(item['identifier'], cat, seq, item['tags'],
                                         resource_listing.parent.joinpath(item['file']))
        else:
            raise CommandError('File \'%s\' not found' % resource_listing)

    def check_args(self, *labels):
        if len(labels) != 1:
            raise CommandError('A single file argument is required')

    def import_item(self, identifier:str, cat:EducatorResourceCategory, seq:int, tags, path:Path):
        resource, created = EducatorResource.objects.get_or_create(identifier=identifier, defaults={
            'sort_order': seq,
        })
        resource.category = cat
        resource.sort_order = seq
        resource.featured = (seq == 0)
        resource.tags = json.dumps(tags)
        resource.save()
        logger.debug('Importing %s from %s%s', identifier, path, ' (NEW)' if created else '')
        try:
            update_resource_from_epub_file(file=path, resource=resource)
        except BadZipFile:
            raise CommandError('Not an EPUB file: %s' % path)
        except Exception as err:
            traceback.print_exc()
            raise CommandError('Error in %s: %s' % (path, err))
