import json
import logging
import os
import textwrap
from base64 import b64encode
from datetime import timedelta, date
from json import JSONDecodeError

from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Sum, Q
from django.utils import timezone

from roster.models import ClusiveUser, Period, Roles, StudentActivitySort
from .util import sort_words_by_frequency

logger = logging.getLogger(__name__)

class Subject(models.Model):
    subject = models.CharField(max_length=256, unique=True)
    # a way to sort or order, especially to separate fiction/non-fiction
    sort_order = models.SmallIntegerField()

    cached_list = None

    class Meta:
        ordering = ['sort_order', 'subject']

    def __str__(self):
        return self.subject

    @classmethod
    def get_list(cls):
        """List of all Subjects.  Cached in memory the first time this method is called."""
        if not cls.cached_list:
            cls.cached_list = list(cls.objects.all())
        return cls.cached_list


class EducatorResourceCategory(models.Model):
    name = models.CharField(max_length=256)
    sort_order = models.SmallIntegerField(unique=True)

    def __str__(self):
        return '<EducatorResourceCategory %s:%s>' % (self.sort_order, self.name)

    class Meta:
        ordering = ['sort_order']


class Book(models.Model):
    """
    Metadata about a single reading, to be represented as an item on the Library page.
    There may be multiple versions of a single Book, which are separate EPUB files.

    If bookshare_id is not null, then this is a book imported from Bookshare.
    These have more restrictive permissions.
    Two Book records can point to the same Bookshare ID since multiple users can load it as their own.
    """
    owner = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    title = models.CharField(max_length=256, db_index=True)
    sort_title = models.CharField(max_length=256, db_index=True)
    author = models.CharField(max_length=256, db_index=True)
    sort_author = models.CharField(max_length=256, db_index=True)
    description = models.TextField(default="", blank=True, db_index=True)
    cover = models.CharField(max_length=256, null=True)
    featured = models.BooleanField(default=False)
    word_count = models.PositiveIntegerField(null=True, db_index=True)
    picture_count = models.PositiveIntegerField(null=True)
    subjects = models.ManyToManyField(Subject, db_index=True)
    bookshare_id = models.CharField(max_length=256, null=True, blank=True, db_index=True)
    add_date = models.DateTimeField(auto_now_add=True, db_index=True)
    # Educator-resource-specific fields.
    # Existence of a non-null resource_identifier marks this as a Resource rather than a Library Book
    resource_identifier = models.CharField(max_length=256, unique=True, db_index=True, null=True, blank=True)
    resource_category = models.ForeignKey(to=EducatorResourceCategory, related_name='resources',
                                          on_delete=models.SET_NULL, null=True, blank=True)
    resource_sort_order = models.SmallIntegerField(null=True, blank=True) # Display order within the category
    resource_tags = models.TextField(null=True, blank=True)

    @property
    def is_educator_resource(self):
        return self.resource_identifier is not None

    @property
    def is_public(self):
        return self.owner is None

    @property
    def is_bookshare(self):
        return self.bookshare_id is not None

    def is_visible_to(self, user : ClusiveUser):
        if self.is_public:
            return True
        if self.owner == user:
            return True
        periods = user.periods.all()
        if BookAssignment.objects.filter(book=self, period__in=periods).exists():
            return True
        return False

    @property
    def resource_tag_list(self):
        """Decode JSON format and return tags as a list."""
        if not hasattr(self, '_resource_tag_list'):
            if self.resource_tags:
                self._resource_tag_list = json.loads(self.resource_tags)
            else:
                self._resource_tag_list = None
        return self._resource_tag_list

    @property
    def all_word_list(self):
        if not hasattr(self, '_all_word_list'):
            versions = self.versions.all()
            if len(versions) == 1:
                self._all_word_list = versions[0].all_word_list
            else:
                words = set()
                for v in versions:
                    words.update(v.all_word_list)
                self._all_word_list = sort_words_by_frequency(words, 'en') # FIXME language of book
        return self._all_word_list

    @property
    def all_word_and_non_dict_word_list(self):
        if not hasattr(self, '_all_word_and_non_dict_word_list'):
            versions = self.versions.all()
            if len(versions) == 1:
                self._all_word_and_non_dict_word_list = versions[0].all_word_list + versions[0].non_dict_word_list
            else:
                words = set()
                for v in versions:
                    words.update(v.all_word_list)
                    words.update(v.non_dict_word_list)
                self._all_word_and_non_dict_word_list = sort_words_by_frequency(words, 'en') # FIXME language of book
        return self._all_word_and_non_dict_word_list

    @property
    def path(self):
        """URL-style path to the book's location."""
        if self.owner:
            return '%d/%d' % (self.owner.pk, self.pk)
        elif self.is_educator_resource:
            return 'resource/%d' % self.pk
        else:
            return 'public/%d' % self.pk

    @property
    def cover_path(self):
        """URL-style path to the book's cover image."""
        if self.cover:
            return self.path + '/' + str(self.cover)
        else:
            return None

    @property
    def storage_dir(self):
        """Path to the filesystem location where this book's files are stored."""
        return default_storage.path(self.path)

    @property
    def cover_storage(self):
        """Path to the place where the cover image for this book is stored."""
        if self.cover:
            return os.path.join(self.storage_dir, str(self.cover))
        else:
            return None

    @property
    def cover_filename(self):
        return os.path.basename(self.cover)

    def set_cover_file(self, filename):
        """
        Updates book, setting the cover to be a given filename; returns the full path to this location.
        Caller is responsible for actually putting a cover image in that location.
        :param filename: name of the cover image file with no path
        :return: full path to where the cover should be stored
        """
        path = os.path.join(self.storage_dir, filename)
        self.cover = filename
        self.save()
        return path

    @property
    def glossary_storage(self):
        return os.path.join(self.storage_dir, 'glossary.json')

    def add_teacher_extra_info(self, periods):
        """
        Adds two fields of additional information for displaying a library card to teachers:
        'assign_list' includes any BookAssignments for this book to the given Periods.
        'custom_list' includes any Customizations for this book to the given Periods.
        :param periods: list of Periods to consider.
        :return: None
        """
        self.assign_list = list(BookAssignment.objects.filter(book=self, period__in=periods))
        self.custom_list = list(Customization.objects.filter(book=self, periods__in=periods))

    def __str__(self):
        if self.is_bookshare:
            return '<Book %d: %s/bookshare/%s>' % (self.pk, self.owner, self.title)
        elif self.is_educator_resource:
            return '<Book %d: Resource %s>' % (self.pk, self.resource_identifier)
        else:
            return '<Book %d: %s/%s>' % (self.pk, self.owner, self.title)

    @classmethod
    def get_featured_books(cls):
        """Return books to suggest to users who have not visited any book yet.
        This is really just a stub so far; returns "Clues to Clusive" if it exists."""
        return Book.objects.filter(owner=None, title__contains='Clusive')

    class Meta:
        ordering = ['title']


class BookVersion(models.Model):
    """Database representation of metadata about a single EPUB file."""
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True, related_name='versions')
    sortOrder = models.SmallIntegerField()
    word_count = models.PositiveIntegerField(null=True)
    picture_count = models.PositiveIntegerField(null=True)
    glossary_words = models.TextField(default="[]")  # Words in the glossary that occur in this version
    all_words = models.TextField(default="[]")  # All dictionary words that occur in this version
    new_words = models.TextField(default="[]")  # Dictionary words that occur in this version but not the previous one.
    non_dict_words = models.TextField(default="[]") # "Words" not in dictionary
    mod_date = models.DateTimeField(default=timezone.now)
    language = models.TextField(max_length=5, default="en-US")
    filename = models.TextField(null=True) # The filename of the EPUB that was uploaded.

    @property
    def path(self):
        """Relative, URL-style path from MEDIA_URL to this book version."""
        return '%s/%d' % (self.book.path, self.sortOrder)

    @property
    def manifest_path(self):
        """Relative, URL-style path from MEDIA_URL to the manifest for this book version."""
        return '%s/manifest.json' % (self.path)

    @property
    def positions_path(self):
        """Relative, URL-style path from MEDIA_URL to the positions for this book version."""
        return '%s/positions.json' % (self.path)

    @property
    def weight_path(self):
        """Relative, URL-style path from MEDIA_URL to the weights for this book version."""
        return '%s/weight.json' % (self.path)

    @property
    def storage_dir(self):
        """Absolute filesystem location of this book version's content."""
        return os.path.join(self.book.storage_dir, str(self.sortOrder))

    @property
    def manifest_file(self):
        """Absolute filesystem location of this book version's manifest."""
        return os.path.join(self.storage_dir, 'manifest.json')

    @property
    def glossary_word_list(self):
        """Decode JSON format and return glossary_words as a list."""
        if not hasattr(self, '_glossary_word_list'):
            self._glossary_word_list = json.loads(self.glossary_words)
        return self._glossary_word_list

    @glossary_word_list.setter
    def glossary_word_list(self, val):
        self._glossary_word_list = val
        self.glossary_words = json.dumps(val)

    @property
    def all_word_list(self):
        """Decode JSON format and return all_words as a list."""
        if not hasattr(self, '_all_word_list'):
            self._all_word_list = json.loads(self.all_words)
        return self._all_word_list

    @all_word_list.setter
    def all_word_list(self, val):
        self._all_word_list = val
        self.all_words = json.dumps(val)

    @property
    def non_dict_word_list(self):
        """Decode JSON format and return non_dict_words as a list."""
        if not hasattr(self, '_non_dict_word_list'):
            self._non_dict_word_list = json.loads(self.non_dict_words)
        return self._non_dict_word_list

    @non_dict_word_list.setter
    def non_dict_word_list(self, val):
        self._non_dict_word_list = val
        self.non_dict_words = json.dumps(val)

    @property
    def new_word_list(self):
        """Decode JSON format and return new_words as a list.
        Cache the list so we don't have to deserialize more than once."""
        if not hasattr(self, '_new_word_list'):
            self._new_word_list = json.loads(self.new_words)
        return self._new_word_list

    @new_word_list.setter
    def new_word_list(self, val):
        self._new_word_list = val
        self.new_words = json.dumps(val)

    @classmethod
    def lookup(cls, book_id, version_number):
        return cls.objects.get(book__pk=book_id, sortOrder=version_number)

    def __str__(self):
        if self.book: #FIXME
            return '<BV %d: %s[%d]>' % (self.pk, self.book, self.sortOrder)
        else:
            return '<BV %d: resource %s>' % (self.pk, self.resource)

    class Meta:
        ordering = ['book', 'sortOrder']
        constraints = [
            models.UniqueConstraint(fields=['book', 'sortOrder'], name='unique_book_version')
        ]


class BookAssignment(models.Model):
    """Records Books that are visible by Periods."""
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True, related_name='assignments')
    period = models.ForeignKey(to=Period, on_delete=models.CASCADE, db_index=True)
    date_assigned = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "[Assigned %s to %s]" % (self.book, self.period)

    class Meta:
        ordering = ['book']
        constraints = [
            models.UniqueConstraint(fields=['book', 'period'], name='unique_book_period')
        ]


class BookTrend(models.Model):
    """
    How popular a Book is for each Period where it has been used.
    The popularity scores is a metric that is increased with each unique user view,
    and decays over time.
    The user count is simply the number of users in this Period that have ever opened the Book.
    It is calculated when requested for a bit of extra efficiency, since it requires a separate query.
    """
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True)
    period = models.ForeignKey(to=Period, on_delete=models.CASCADE, db_index=True)
    popularity = models.IntegerField(default=0)
    _user_count = models.IntegerField(null=True, blank=True)

    def record_new_view(self):
        # Popularity points for a single user view are from 1 (14 days ago) to 2**14 = 16384 (today)
        self.popularity += 2**14
        self._user_count = None   # Force recalculation when next accessed
        self.save()

    @property
    def user_count(self):
        if self._user_count is None:
            self._user_count = Paradata.objects.filter(user__periods=self.period, user__role=Roles.STUDENT,
                                                       book=self.book, view_count__gt=0).count()
            logger.debug('Calculated user count for %s = %d', self, self._user_count)
            self.save()
        return self._user_count

    def __str__(self):
        return '<BookTrend %s/%s>' % (self.book, self.period)

    @classmethod
    def top_trends(cls, period):
        return cls.objects.filter(period=period, book__resource_identifier__isnull=True)\
            .order_by('-popularity')

    @classmethod
    def top_assigned(cls, period):
        return cls.objects.filter(period=period, book__resource_identifier__isnull=True,
                                  book__assignments__period=period)\
            .order_by('-popularity')

    @classmethod
    def update_all_trends(cls):
        for period in Period.objects.all():
            logger.debug('Updating trends for %s', period)
            cls.update_trends_for_period(period)

    @classmethod
    def update_trends_for_period(cls, period):
        # All trends for this period will be updated.
        trends = BookTrend.objects.filter(period=period)
        # This should return a record for each user in the period for each book they've visited.
        paras = Paradata.objects.filter(user__periods=period)
        # Get daily activity on these items for the last 14 days.
        today = date.today()
        earliest = today - timedelta(days=14)
        dailies = ParadataDaily.objects.filter(paradata__in=paras, date__gt=earliest)
        # Sum up activity of all Period users
        scores = {}
        for d in dailies:
            days_ago = (today - d.date).days
            points = 2 ** (14-days_ago)
            if d.paradata.book in scores:
                scores[d.paradata.book] += points
            else:
                scores[d.paradata.book] = points
        # Update existing BookTrend objects
        for t in trends:
            if t.book in scores:
                logger.debug('  %s pop was %d now %d', t, t.popularity, scores[t.book])
                t.popularity = scores[t.book]
                del scores[t.book]
            else:
                logger.debug('  %s pop was %d now none', t, t.popularity)
                t.popularity = 0
            t.save()
        # Create any new BookTrend objects
        for book in scores:
            logger.debug('  New trend for book %s score %d', book, scores[book])
            b = BookTrend(book=book, period=period, popularity=scores[book])
            b.save()


class Paradata(models.Model):
    """Information about a User's interactions with a Book."""
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)

    view_count = models.SmallIntegerField(default=0, verbose_name='View count')
    last_view = models.DateTimeField(null=True, verbose_name='Last view time')
    first_version = models.ForeignKey(to=BookVersion, on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name='Original version chosen by system', related_name='paradata_first_version_set')
    last_version = models.ForeignKey(to=BookVersion, on_delete=models.SET_NULL, null=True, blank=True,
                                     verbose_name='Last version viewed', related_name='paradata_last_version_set')
    last_location = models.TextField(null=True, verbose_name='Last reading location')
    total_time = models.DurationField(null=True, verbose_name='Total active time spent in book')
    words_looked_up = models.TextField(null=True, blank=True, verbose_name='JSON list of words looked up')
    read_aloud_count = models.SmallIntegerField(default=0, verbose_name='Read-aloud use count')
    translation_count = models.SmallIntegerField(default=0, verbose_name='Translation use count')
    starred = models.BooleanField(null=False, default=False)
    starred_date = models.DateTimeField(null=True, blank=True)

    @property
    def words_looked_up_list(self):
        val = self.words_looked_up
        if val:
            return json.loads(val)
        else:
            return []

    @classmethod
    def record_view(cls, book, version_number, clusive_user):
        """Update Paradata and ParadataDaily records to a view for the given book, user, version, and time."""
        bv = BookVersion.objects.get(book=book, sortOrder=version_number)
        para, created = cls.objects.get_or_create(book=book, user=clusive_user)
        para.view_count += 1
        para.last_view = timezone.now()
        if not para.first_version:
            para.first_version = bv
        if para.last_version != bv:
            # If we're switching to a different version, clear out last reading location
            para.last_location = None
            para.last_version = bv
        para.save()

        parad, pd_created = ParadataDaily.objects.get_or_create(paradata=para, date=date.today())
        parad.view_count += 1
        parad.save()
        if pd_created:
            # A new view today -> the BookTrend should be boosted.
            for p in clusive_user.periods.all():
                bt, bt_created = BookTrend.objects.get_or_create(book=book, period=p)
                bt.record_new_view()

        return para

    @classmethod
    def record_last_location(cls, book_id, version, user, locator):
        b = Book.objects.get(pk=book_id)
        para, created = cls.objects.get_or_create(book=b, user=user)
        if para.last_version.sortOrder == version:
            para.last_location = locator
            para.last_view = timezone.now()
            para.save()
            logger.debug('Set last reading location for %s', para)
        else:
            logger.debug('Book version has changed since this location was recorded, ignoring. %d but we have %d',
                         version, para.last_version.sortOrder)

    @classmethod
    def record_additional_time(cls, book_id, user, time):
        """Update Paradata and ParadataDaily tables with the time increment specified"""
        b = Book.objects.get(pk=book_id)
        para, created = cls.objects.get_or_create(book=b, user=user)
        if para.total_time is None:
            para.total_time = timedelta()
        para.total_time += time
        para.save()

        today = date.today()
        parad, created = ParadataDaily.objects.get_or_create(paradata=para, date=today)
        if parad.total_time is None:
            parad.total_time = timedelta()
        parad.total_time += time
        parad.save()

    @classmethod
    def record_word_looked_up(cls, book, user, word):
        """Update Paradata with the new lookup"""
        para, created = cls.objects.get_or_create(book=book, user=user)
        if para.words_looked_up:
            words = json.loads(para.words_looked_up)
        else:
            words = []
        if not word in words:
            words.append(word)
            words.sort()
            para.words_looked_up = json.dumps(words)
            logger.debug('Updated %s with new words_looked_up list: %s', para, para.words_looked_up)
            para.save()

    @classmethod
    def record_starred(cls, book_id, clusive_user_id, starred):
        # record the starred (favorite) value for this para
        user_object = ClusiveUser.objects.get(pk=clusive_user_id)
        book_object = Book.objects.get(pk=book_id)
        para, created = cls.objects.get_or_create(book=book_object, user=user_object)
        para.starred = starred
        if para.starred:
            para.starred_date = timezone.now()
        else:
            para.starred_date = None
        para.save()

    @classmethod
    def record_translation(cls, book, user):
        para, created = cls.objects.get_or_create(book=book, user=user)
        para.translation_count += 1
        para.save()

    @classmethod
    def record_read_aloud(cls, book, user):
        para, created = cls.objects.get_or_create(book=book, user=user)
        para.read_aloud_count += 1
        para.save()

    def __str__(self):
        return "%s@%s" % (self.user, self.book)

    @classmethod
    def latest_for_user(cls, user: ClusiveUser, max=10):
        """Return a QuerySet for Paradatas for a user with most recent last_view time"""
        return Paradata.objects.filter(user=user, last_view__isnull=False).order_by('-last_view')

    @classmethod
    def reading_data_for_period(cls, period: Period, days=0, sort='name'):
        """
        Calculate time, number of books, and individual book stats for each user in the given Period.
        :param period: group of students to consider
        :param days: number of days before and including today. If 0 or omitted, include all time.
        :return: a list of {clusive_user: u, book_count: n, total_time: t, books: [bookinfo, bookinfo,...] }
        """
        students = period.users.filter(role=Roles.STUDENT)
        assigned_books = [a.book for a in period.bookassignment_set.all()]
        map = {s:{'clusive_user': s, 'book_count': 0, 'hours':0, 'books': []} for s in students}
        one_hour: timedelta = timedelta(hours=1)
        # Query for all Paradata records showing book views for these students
        paradatas = Paradata.objects.filter(user__in=students)
        # If we're date limited, annotate this query with information from ParadataDaily
        if days:
            start_date = date.today()-timedelta(days=days)
            logger.debug('Query dailies since %s', start_date)
            paradatas = paradatas.annotate(recent_time=Sum('paradatadaily__total_time',
                                                        filter=Q(paradatadaily__date__gt=start_date)))
        for p in paradatas:
            # Skip if time is zero.
            if days:
                if not p.recent_time:
                    continue
            else:
                if not p.total_time:
                    continue
                p.recent_time = p.total_time
            # add to entry map
            entry = map[p.user]
            entry['book_count'] += 1
            entry['hours'] += p.recent_time/one_hour
            entry['books'].append({
                'book_id': p.book.id,
                'title': p.book.title,
                'hours': p.recent_time/one_hour,
                'is_assigned': p.book in assigned_books,
            })
        # Add a percent_time field to each item.
        # This is the fraction of the largest total # of hours for any student.
        if map:
            max_hours = max([e['hours'] for e in map.values()])
            for s, entry in map.items():
                for p in entry['books']:
                    if p['hours']:
                        p['percent_time'] = round(100*p['hours']/max_hours)
                    else:
                        p['percent_time'] = 0
                # Sort book entries by time
                entry['books'].sort(reverse=True, key=lambda p: p['hours'])
                # Combine low-time items into an "other" item.
                # First item is never considered "other".
                if len(entry['books']) > 2:
                    too_small_items = list(filter(lambda p: p['percent_time']<10, entry['books'][1:]))
                    if len(too_small_items) > 1:
                        # Remove the too-small items from the main list
                        del entry['books'][-len(too_small_items):]
                        # Make an "other" item.
                        other_hours = sum(item['hours'] for item in too_small_items)
                        entry['books'].append({
                            'book_id': 0,
                            'title': '%d other books' % (len(too_small_items)),
                            'hours': other_hours,
                            'percent_time': round(100*other_hours/max_hours),
                            'is_assigned': False,
                            'is_other': True,
                        })

        # Return value is a sorted list for display.
        result = list(map.values())
        # First sort by name, even if something else is the primary sort, so that zeros are alphabetical
        result.sort(key=lambda item: item['clusive_user'].user.first_name.lower())
        if sort == StudentActivitySort.COUNT:
            result.sort(reverse=True, key=lambda item: item['book_count'])
        elif sort == StudentActivitySort.TIME:
            result.sort(reverse=True, key=lambda item: item['hours'])

        return result

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['book', 'user'], name='unique_book_user')
        ]


class ParadataDaily(models.Model):
    """
    Slice of Paradata for a particular date.
    Used for efficiently constructing dashboard views and calculating trends.
    """
    paradata = models.ForeignKey(to=Paradata, on_delete=models.CASCADE, db_index=True)
    date = models.DateField(default=date.today, db_index=True)

    view_count = models.SmallIntegerField(default=0, verbose_name='View count on date')
    total_time = models.DurationField(null=True, verbose_name='Reading time on date')


class Annotation(models.Model):
    """Holds one highlight/bookmark/annotation/note"""
    bookVersion = models.ForeignKey(to=BookVersion, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)
    highlight = models.TextField()
    progression = models.FloatField()   # Location in the book, expressed as a number from 0 to 1
    dateAdded = models.DateTimeField(default=timezone.now)
    dateDeleted = models.DateTimeField(null=True, blank=True, db_index=True)
    note = models.TextField(null=True, blank=True)

    @property
    def highlight_object(self):
        """Returns the 'highlight' string converted to a python object (a dictionary)."""
        return json.loads(self.highlight)

    @highlight_object.setter
    def highlight_object(self, value):
        self.highlight = json.dumps(value)

    @property
    def highlight_base64(self):
        """Return highlight string Base64-encoded so it can be passed as an HTML attribute value."""
        return b64encode(self.highlight.encode('utf-8')).decode()

    def clean_text(self):
        try:
            return self.highlight_object['highlight']['selectionInfo']['cleanText']
        except KeyError:
            return None

    def clean_text_limited(self):
        return textwrap.shorten(self.clean_text(), 200, placeholder='…')

    def update_id(self):
        """Rewrite JSON with the database ID as the annotation's ID
        so that client & server agree on one ID."""
        hl = self.highlight_object
        hl['id'] = self.pk
        self.highlight_object = hl

    def update_progression(self):
        """Set the 'progression' field based on the highlight."""
        self.progression = self.find_progression(self.highlight)

    def find_progression(self, jsonString):
        if jsonString is None:
            return 0
        try:
            locations = json.loads(jsonString).get('locations')
            return locations.get('totalProgression')
        except (JSONDecodeError, AttributeError):
            logger.error('Can\'t find progression in JSON %s', jsonString)
            return 0

    @classmethod
    def get_list(cls, user, book_version):
        return cls.objects.filter(user=user, bookVersion=book_version, dateDeleted=None)

    def __str__(self):
        return "[Annotation %d for %s]" % (self.pk, self.user)

    class Meta:
        ordering = ['progression']

class Customization(models.Model):
    """Hold customizations for a Book as used in zero or more Periods"""
    owner = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True)
    periods = models.ManyToManyField(Period, blank=True, related_name='customizations', db_index=True)
    title = models.CharField(max_length=256, default='Customization', blank=False)
    question = models.CharField(max_length=256, default='', blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    @property
    def word_list(self):
        words = []
        for custom_vocabulary_word in self.customvocabularyword_set.all():
            words.append(custom_vocabulary_word.word)
        return words

    @classmethod
    def get_customization_for_user(cls, book, clusive_user):
        result = cls.objects.filter(book=book, periods=clusive_user.current_period)
        return result[0] if result else None

    @classmethod
    def get_customizations(cls, book, periods, owner):
        return cls.objects \
            .filter(Q(book=book)
                    & (Q(periods__in=periods) | Q(owner=owner))) \
            .distinct()

    def __str__(self):
        return '<Customization %s: %s %s>' % (self.pk, self.title, self.book)

    class Meta:
        ordering = ['book', 'title']

class CustomVocabularyWord(models.Model):
    """A word used in a Customization"""
    customization = models.ForeignKey(to=Customization, on_delete=models.CASCADE, db_index=True)
    word = models.CharField(max_length=256, default='', blank=True)

    def __str__(self):
        return '[CustomVocabularyWord %s for %s]' % (self.word, self.customization)

