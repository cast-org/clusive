import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.models import Book

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Merge two Books in case a new version has been mistakenly added to the library. ' \
           'First argument should be the book to delete, second is the book to keep (merge into).' \
           'Comprehension and affect checks, assignments, and Paradata will be moved to the kept Book. ' \
           'Just does a dry run unless --yes argument is given.' \
           'If only one argument is supplied, will just print some basic info on that book.' \
           'If no arguments are supplied, prints out the list of books and IDs.'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true')
        parser.add_argument('merge', type=int, nargs='?')
        parser.add_argument('keep', type=int, nargs='?')

    def handle(self, *args, **options):
        if not options['merge']:
            self.stdout.write('No book[s] specified, printing list:')
            all_public = Book.objects.filter(owner=None).all().order_by('title')
            for b in all_public:
                self.stdout.write('%03d %s' % (b.id, b.title))
            return

        if not options['keep']:
            self.stdout.write('Info on book %d' % options['merge'])
            self.print_book_info(options['merge'])
            return

        merge : Book
        keep : Book
        merge = Book.objects.get(id=options['merge'])
        keep = Book.objects.get(id=options['keep'])

        self.stdout.write('Merging book: %s (WILL DELETE)' % self.style.ERROR(merge.title))
        self.stdout.write('        into: %s' % self.style.SUCCESS(keep.title))

        if options['yes']:
            self.stdout.write('REALLY')
        else:
            self.stdout.write('Dry run.')

        if merge.owner != keep.owner:
            raise CommandError('Books have different owners, will not merge')

        assign = merge.assignments.all()
        self.stdout.write('Assignments         : %d -> %d' % (len(assign), keep.assignments.count()))

        ccrs = merge.comprehensioncheckresponse_set.all()
        self.stdout.write('Comprehension checks: %d -> %d' % (len(ccrs), keep.comprehensioncheckresponse_set.count()))

        acrs = merge.affectivecheckresponse_set.all()
        self.stdout.write('Affect checks       : %d -> %d' % (len(acrs), keep.affectivecheckresponse_set.count()))

        para = merge.paradata_set.all()
        self.stdout.write('Paradata            : %d -> %d' % (len(para), keep.paradata_set.count()))

        if options['yes']:
            with transaction.atomic():
                for item in assign:
                    item.book = keep
                    item.save()
                for item in ccrs:
                    item.book = keep
                    item.save()
                for item in acrs:
                    item.book = keep
                    item.save()
                for item in para:
                    item.book = keep
                    item.save()
                merge.delete()
            self.stdout.write(self.style.SUCCESS('Done'))
        else:
            self.stdout.write('To really merge them, add --yes flag to command')

    def print_book_info(self, id):
        try:
            b = Book.objects.get(id=id)
            self.stdout.write('Title: %s' % b.title)
            if b.owner:
                self.stdout.write('Owner: %s' % b.owner.username)
            else:
                self.stdout.write('Public book')
            self.stdout.write('Assignments         : %d' % b.assignments.count())
            self.stdout.write('Comprehension checks: %d' % b.comprehensioncheckresponse_set.count())
            self.stdout.write('Affect checks       : %d' % b.affectivecheckresponse_set.count())
            self.stdout.write('Paradata            : %d' % b.paradata_set.count())
        except Book.DoesNotExist:
            self.stderr.write('No book with id %d' % id)

