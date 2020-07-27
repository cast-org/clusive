from django.db import models

# Create your models here.

class MessageTypes:
    PREF_CHANGE = 'PC'

    CHOICES = [
        (PREF_CHANGE, 'Preference Change'),
    ]    

class Message(models.Model):
    type = models.CharField(max_length=10, choices=MessageTypes.CHOICES)
    timestamp = models.DateTimeField()
    content = models.TextField(max_length=500)