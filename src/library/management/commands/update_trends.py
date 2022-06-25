import logging

from django.core.management.base import BaseCommand

from library.models import BookTrend

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update the data on trending books in each classroom. Should be run once per day.'

    def handle(self, *args, **options):
        BookTrend.update_all_trends()
