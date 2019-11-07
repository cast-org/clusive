from django.db import models


class Book(models.Model):
    path = models.CharField(max_length=256)
    title = models.CharField(max_length=256)
    description = models.TextField(default="")
    cover = models.CharField(max_length=256, null=True)
    glossary_words = models.TextField(default="[]")
    all_words = models.TextField(default="[]")

    class Meta:
        ordering = ['title']
