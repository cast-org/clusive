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
    glossary_words = models.TextField(default="[]")
    all_words = models.TextField(default="[]")

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
    def record_view(cls, path, versionNumber, user):
        b = Book.objects.get(path=path)
        bv = BookVersion.objects.get(book__path=path, sortOrder=versionNumber)
        para, created = cls.objects.get_or_create(book=b, user=user)
        para.viewCount += 1
        para.lastVersion = bv
        para.save()

    @classmethod
    def record_last_location(cls, path, user, locator):
        b = Book.objects.get(path=path)
        para, created = cls.objects.get_or_create(book=b, user=user)
        para.lastLocation = locator
        para.save()

    def __str__(self):
        return "%s@%s" % (self.user, self.book)