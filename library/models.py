from django.db import models

class Book(models.Model):
    path = models.CharField(max_length=256)
    title = models.CharField(max_length=256)
    cover = models.CharField(max_length=256, null=True)

    class Meta:
        ordering = ['title']
