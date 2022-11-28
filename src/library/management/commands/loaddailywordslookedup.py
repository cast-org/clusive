import json
import logging

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from eventlog.models import Event
from library.models import DailyWordsLookedUp
from roster.models import ClusiveUser, Period
import pdb

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update the DailyWordList table based on the Event records. \n'\
           'Usage: python manage.py BatchLoadDailyWordLIsts username periodname'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='?', type=str)
        parser.add_argument('periodname', nargs='?', type=str)

    def handle(self, *args, **options):
        username = options['username']
        periodname = options['periodname']
        try:
            self.period = Period.objects.get(name=periodname)            
            self.clusive_user = ClusiveUser.objects.get(
                user__username=username,
                periods__in=[self.period]
            )
            # Get all the avents for the user/period which involve word lookup
            word_events = Event.objects.filter(
                actor=self.clusive_user,
                group=self.period,
                control__icontains='lookup'
            ).order_by('event_time')
            # Get the first event in time and gather all the others at the same
            # day
            first_event = word_events.first()
            one_days_worth = word_events.filter(
                event_time__date=first_event.event_time.date()
            )
            the_rest = word_events
            # Loop to make a DailyWordsLookedUp record for a group of "lookup"
            # Events that all occurred on the same day.  Then, find the next
            # group of events that occurred on the next day in the event list.
            while True:
                daily_word_list = self.make_one_record(one_days_worth)
                logger.debug(f"DailyWordList list for {first_event.event_time} is {daily_word_list}")
                the_rest = the_rest.exclude(
                    pk__in=one_days_worth.values_list('pk', flat=True)
                )
                first_event = the_rest.first()
                if first_event is None:
                    break
                else:
                    one_days_worth = the_rest.exclude(
                        event_time__gt=first_event.event_time
                    )
            logger.info('Done, found ' + str(word_events.count()) + ' events')

        except Period.DoesNotExist:
            logger.error(f"No such period: '{periodname}'")

        except ClusiveUser.DoesNotExist:
            logger.error(f"No user named '{username}' in '{periodname}'")
    
    def make_one_record(self, one_days_worth: QuerySet):
        word_set = set()
        for word_event in one_days_worth:
            if word_event.value:
                word_set.add(word_event.value)

        if len(word_set) > 0:
            word_list = list(word_set)
            daily_word_list = DailyWordsLookedUp.objects.create(
                user=self.clusive_user,            
                period=self.period,
                day_looked_up=one_days_worth.first().event_time.date(),
                words_looked_up=json.dumps(word_list)
            )
            daily_word_list.save()
            logger.info(f"Made a DailyWordsLookedUp {word_list} for {daily_word_list.day_looked_up}")
        return word_list
