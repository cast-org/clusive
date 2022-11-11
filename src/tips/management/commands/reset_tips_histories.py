import logging
from django.core.management.base import BaseCommand, CommandError

from roster.models import ClusiveUser
from tips.models import TipHistory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'In the tip history table, reset these field values:\n' \
           '1. reset the show count to 0\n' \
           '2. reset all timestamps to null including the last show, the last attempt and the last action\n' \
           'If a user name is given as an argument, above values for this user will be reset.\n' \
           'If no argument is given, all above values in the tip history table will be reset.\n' \
           '\n'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='?', type=str)

    def handle(self, *args, **options):
        uname = options['username']
        if uname:
            try:
                clusive_user = ClusiveUser.objects.get(user__username=uname)
            except ClusiveUser.DoesNotExist:
                raise CommandError('User name \'%s\' not found' % uname)
            self.reset_one_user_tip_history(clusive_user.id, uname)
        else:
            self.reset_all_tip_histories()

    def reset_a_tip_history(self, tip_history):
        tip_history.show_count = 0
        tip_history.last_attempt = None
        tip_history.last_show = None
        tip_history.last_action = None
        tip_history.save()

    def reset_one_user_tip_history(self, uid, uname):
        for tip_history in TipHistory.objects.filter(user_id=uid):
            self.reset_a_tip_history(tip_history)
        logger.info("Done: the tip history is reset for the user '" + uname + "'")

    def reset_all_tip_histories(self):
        for tip_history in TipHistory.objects.all():
            self.reset_a_tip_history(tip_history)
        logger.info("Done: all tip histories are reset")
