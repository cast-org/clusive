from django.core.management.base import BaseCommand, CommandError

from django.contrib.auth.models import User
from tips.models import TipHistory

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
            user = User.objects.filter(username=uname)
            if user:
                self.reset_one_user_tip_history(user[0].id, uname)
            else:
                raise CommandError('User name \'%s\' not found' % uname)
        else:
            self.reset_all_tip_histories()

    def reset_a_tip_history(self, tip):
        tip.show_count = 0
        tip.last_attempt = None
        tip.last_show = None
        tip.last_action = None
        tip.save()

    def reset_one_user_tip_history(self, uid, uname):
        for tip in TipHistory.objects.filter(user_id=uid):
            tip = self.reset_a_tip_history(tip)
        self.stdout.write("Done: the tip history is reset for the user '" + uname + "'")

    def reset_all_tip_histories(self):
        for tip in TipHistory.objects.all():
            tip = self.reset_a_tip_history(tip)
        self.stdout.write("Done: all tip histories are reset")
