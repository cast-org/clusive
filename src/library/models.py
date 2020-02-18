from django.db import models


class Book(models.Model):
    path = models.CharField(max_length=256)
    title = models.CharField(max_length=256)
    description = models.TextField(default="")
    cover = models.CharField(max_length=256, null=True)

    def __str__(self):
        return self.path

    class Meta:
        ordering = ['title']


class BookVersion(models.Model):
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE)
    sortOrder = models.SmallIntegerField()
    glossary_words = models.TextField(default="[]")
    all_words = models.TextField(default="[]")

    @classmethod
    def lookup(cls, path, versionNumber):
        return cls.objects.get(book__path=path, sortOrder=versionNumber)

    def __str__(self):
        return "%s[%d]" % (self.book.title, self.sortOrder)

    class Meta:
        ordering = ['book', 'sortOrder']
