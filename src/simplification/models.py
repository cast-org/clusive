from datetime import date

from django.db import models


class PictureSource:
    NOUN_PROJECT = 'NP'
    FLATICON = 'FI'

    CHOICES = [
        (NOUN_PROJECT, 'Noun Project'),
        (FLATICON, 'Flaticon'),
    ]


class PictureUsage(models.Model):
    """
    Data detailing pictures retrieved from an API and used for simplification.
    The icon_id is assigned by the online service (Noun Project or Flaticon).
    If the icon_id is null it means the given service did not find any relevant icon for the word.
    """
    date = models.DateField(auto_now_add=True)
    source = models.CharField(max_length=4, choices=PictureSource.CHOICES)
    word = models.CharField(max_length=256)
    icon_id = models.IntegerField(null=True, blank=True)
    count = models.IntegerField(default=0)

    @classmethod
    def log_usage(cls, source, word, icon_id):
        record, created = cls.objects.get_or_create(date=date.today(), source=source, word=word, icon_id=icon_id)
        record.count += 1
        record.save()

    @classmethod
    def log_missing(cls, source, word):
        record, created = cls.objects.get_or_create(date=date.today(), source=source, word=word, icon_id=None)
        record.count += 1
        record.save()
