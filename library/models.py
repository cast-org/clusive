from django.db import models

class Book(models.Model):
    path = models.CharField(max_length=256)
    title = models.CharField(max_length=256)

