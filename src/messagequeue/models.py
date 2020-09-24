from django.db import models

# Create your models here.

import django.dispatch

client_side_prefs_change = django.dispatch.Signal(providing_args=["timestamp", "content", "request"])

class Message:
    class AllowedTypes:
        PREF_CHANGE = 'PC'

    def __init__(self, type, timestamp, content, request):
        self.type = type
        self.timestamp = timestamp 
        self.content = content
        self.request = request        

    def send_signal(self):
        if(self.type == Message.AllowedTypes.PREF_CHANGE):
            self.send_client_side_prefs_change()

    def send_client_side_prefs_change(self):
        client_side_prefs_change.send(sender=self.__class__, timestamp=self.timestamp, content=self.content, request=self.request)