import json
import logging
import os
import textwrap
from base64 import b64encode
from datetime import timedelta
from json import JSONDecodeError

from django.core.files.storage import default_storage
from django.db import models
from django.utils import timezone

from roster.models import ClusiveUser, Period

logger = logging.getLogger(__name__)

class Subject(models.Model):
    subject = models.CharField(max_length=256, unique=True)
    # a way to sort or order, especially to separate fiction/non-fiction
    sortOrder = models.SmallIntegerField()

    class Meta:
        ordering = ['subject']

    def __str__(self):
        return self.subject


class Book(models.Model):
    """Metadata about a single reading, to be represented as an item on the Library page.
    There may be multiple versions of a single Book, which are separate EPUB files."""
    owner = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=256)
    sort_title = models.CharField(max_length=256)
    author = models.CharField(max_length=256)
    sort_author = models.CharField(max_length=256)
    description = models.TextField(default="", blank=True)
    cover = models.CharField(max_length=256, null=True)
    word_count = models.PositiveIntegerField(null=True)
    picture_count = models.PositiveIntegerField(null=True)
    subjects = models.ManyToManyField(Subject)

    @property
    def is_public(self):
        return self.owner is None

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
    def path(self):
        """URL-style path to the book's location."""
        if self.owner:
            return '%d/%d' % (self.owner.pk, self.pk)
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
    def glossary_storage(self):
        return os.path.join(self.storage_dir, 'glossary.json')

    def __str__(self):
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
        return '<BV %d: %s[%d]>' % (self.pk, self.book, self.sortOrder)

    class Meta:
        ordering = ['book', 'sortOrder']
        constraints = [
            models.UniqueConstraint(fields=['book', 'sortOrder'], name='unique_book_version')
        ]


class BookAssignment(models.Model):
    """Records Books that are visible by Periods."""
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True, related_name='assignments')
    period = models.ForeignKey(to=Period, on_delete=models.CASCADE, db_index=True)
    dateAssigned = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "[Assigned %s to %s]" % (self.book, self.period)

    class Meta:
        ordering = ['book']
        constraints = [
            models.UniqueConstraint(fields=['book', 'period'], name='unique_book_period')
        ]


class Paradata(models.Model):
    """Information about a User's interactions with a Book."""
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)

    view_count = models.SmallIntegerField(default=0, verbose_name='View count')
    last_view = models.DateTimeField(null=True, verbose_name='Last view time')
    last_version = models.ForeignKey(to=BookVersion, on_delete=models.SET_NULL, null=True,
                                     verbose_name='Last version viewed')
    last_location = models.TextField(null=True, verbose_name='Last reading location')
    total_time = models.DurationField(null=True, verbose_name='Total time spent in book')

    @classmethod
    def record_view(cls, book, version_number, clusive_user):
        bv = BookVersion.objects.get(book=book, sortOrder=version_number)
        para, created = cls.objects.get_or_create(book=book, user=clusive_user)
        para.view_count += 1
        para.last_view = timezone.now()
        if para.last_version != bv:
            # If we're switching to a different version, clear out last reading location
            para.last_location = None
            para.last_version = bv
        para.save()
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
        b = Book.objects.get(pk=book_id)
        para, created = cls.objects.get_or_create(book=b, user=user)
        if para.total_time is None:
            para.total_time = timedelta()
        para.total_time += time
        para.save()

    def __str__(self):
        return "%s@%s" % (self.user, self.book)

    @classmethod
    def latest_for_user(cls, user: ClusiveUser, max=10):
        """Return a QuerySet for Paradatas for a user with most recent last_view time"""
        return Paradata.objects.filter(user=user, last_view__isnull=False).order_by('-last_view')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['book', 'user'], name='unique_book_user')
        ]


class Annotation(models.Model):
    """Holds one highlight/bookmark/annotation/note"""
    bookVersion = models.ForeignKey(to=BookVersion, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)
    highlight = models.TextField()
    progression = models.FloatField()   # Location in the book, expressed as a number from 0 to 1
    dateAdded = models.DateTimeField(default=timezone.now)
    dateDeleted = models.DateTimeField(null=True, db_index=True)

    # later: note
    # later: category

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
            return locations.get('progression')
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

