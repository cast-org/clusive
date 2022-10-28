import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from tips.models import TipType

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Beginnig with the TipType with the least priority, loop\n' \
            'through all TipTypes decreassing their priority by 1 (one).\n' \
            'Only do this if you have prefiously increased the priority.\n' \

    def handle(self, *args, **options):
        tip_types = TipType.objects.all().order_by('priority')
        for tip in tip_types:
            tip.priority -= 1
            tip.save()
            logger.debug(f"Updated {tip}'s priority to {tip.priority}")
        logger.debug("Done")
