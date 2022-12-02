import json
import logging
import sys

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from roster.models import ClusiveUser
from library.models import Paradata, ParadataDaily
from eventlog import Event

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sanity check:  for a given Paradata, does its `words_looked_up`\n' \
           'match the union of its ParadataDaily records\'\n' \
           '`words_looked_up` fields?'

    def handle(self, *args, **options):
        users = ClusiveUser.objects.all()
        for clusive_user in users:
            for paradata in Paradata.objects.filter(user=clusive_user):
                self.sanity_check(paradata)
        logger.info('Done')

    def sanity_check(self, paradata: Paradata):
        dailies = ParadataDaily.objects.filter(
            paradata__user=paradata.user,
            paradata__book=paradata.book
        )
        union_words = set()
        for paradata_daily in dailies:
            daily_words = set(json.loads(paradata_daily.words_looked_up or '[]'))
            union_words = union_words.union(daily_words)

        paradata_words = json.loads(paradata.words_looked_up or '[]')
        if union_words != set(paradata_words):
            logger.error(f"Union of ParadataDaily 'words_looked_up' do not match the associated {paradata}")
            logger.error(f"    Union: {list(union_words)}")
            logger.error(f"    Paradata: {paradata_words}")
            logger.error('')
