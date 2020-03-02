import json

from django.db import models

from roster.models import ClusiveUser


class Book(models.Model):
    path = models.CharField(max_length=256, db_index=True)
    title = models.CharField(max_length=256)
    description = models.TextField(default="")
    cover = models.CharField(max_length=256, null=True)

    def __str__(self):
        return self.path

    class Meta:
        ordering = ['title']


class BookVersion(models.Model):
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True)
    sortOrder = models.SmallIntegerField()
    glossary_words = models.TextField(default="[]")  # Words in the glossary that occur in this version
    all_words = models.TextField(default="[]")       # All words that occur in this version
    new_words = models.TextField(default="[]")       # Words that occur in this version but not the previous one.

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
    def lookup(cls, path, versionNumber):
        return cls.objects.get(book__path=path, sortOrder=versionNumber)

    def __str__(self):
        return "%s[%d]" % (self.book, self.sortOrder)

    class Meta:
        ordering = ['book', 'sortOrder']


class Paradata(models.Model):
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)

    viewCount = models.SmallIntegerField(default=0, verbose_name='View count')
    lastVersion = models.ForeignKey(to=BookVersion, on_delete=models.SET_NULL, null=True,
                                    verbose_name='Last version viewed')
    lastLocation = models.TextField(null=True, verbose_name='Last reading location')

    @classmethod
    def record_view(cls, book, versionNumber, clusive_user):
        bv = BookVersion.objects.get(book=book, sortOrder=versionNumber)
        para, created = cls.objects.get_or_create(book=book, user=clusive_user)
        para.viewCount += 1
        para.lastVersion = bv
        para.save()
        return para

    @classmethod
    def record_last_location(cls, path, user, locator):
        b = Book.objects.get(path=path)
        para, created = cls.objects.get_or_create(book=b, user=user)
        para.lastLocation = locator
        para.save()

    def __str__(self):
        return "%s@%s" % (self.user, self.book)