import random
from datetime import timedelta

import lorem
from django.core.management.base import BaseCommand, CommandError

from assessment.models import ComprehensionCheckResponse, ComprehensionCheck
from library.models import Book, Paradata
from roster.models import ClusiveUser

sample_users = [
    'samstudent',
    'sarahstudent',
    'sashastudent',
    'salstudent',
]

def fake_comp_check(book, user):
    scale_value = random.choice(ComprehensionCheck.ComprehensionScale.COMPREHENSION_SCALE_CHOICES)[0]
    r, created = ComprehensionCheckResponse.objects.get_or_create(user=user,
                                                                  book=book,
                                                                  comprehension_scale_response=scale_value,
                                                                  comprehension_free_response=lorem.get_sentence())
    if created:
        print('  Created new comp check for %s' % user)
        r.save()
    else:
        print('  Comp check already existed for %s' % user)

    return r

def fake_read(book, user):
    Paradata.record_view(book, 0, user)
    Paradata.record_additional_time(book_id=book.id, user=user, time=timedelta(minutes=random.randint(0, 60)))


def create_random_comp_checks(users):
    # Choose 3 random books
    all_books = list(Book.objects.all())
    try:
        books = random.sample(all_books, 3)
    except:
        raise CommandError('Could not find 3 books, is the library empty?')
    for b in books:
        print('Reading: %s' % b.title)
        for u in users:
            fake_read(b, u)
            fake_comp_check(b, u)


class Command(BaseCommand):
    help = 'Create sample comprehension checks for 3 randomly-chosen books' \
           ' and the users created by "createrostersamples" command'

    def handle(self, *args, **options):
        users = ClusiveUser.objects.filter(user__username__in=sample_users)
        if not users:
            raise CommandError('Could not find users. Did you run "createrostersamples" command?')
        create_random_comp_checks(users)


