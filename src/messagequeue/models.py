from django.db import models

# Create your models here.

import django.dispatch

import logging

logger = logging.getLogger(__name__)

client_side_prefs_change = django.dispatch.Signal(providing_args=["timestamp", "content", "request"])

class Message:
    class AllowedTypes:
        PREF_CHANGE = 'PC'  
        CALIPER_EVENT = 'CE'      

    def __init__(self, type, timestamp, content, request):
        self.type = type
        self.timestamp = timestamp 
        self.content = content
        self.request = request        

    def send_signal(self):
        if(self.type == Message.AllowedTypes.PREF_CHANGE):
            self.send_client_side_prefs_change()
        if(self.type == Message.AllowedTypes.CALIPER_EVENT):
            self.send_client_side_caliper_event()

    def send_client_side_prefs_change(self):
        client_side_prefs_change.send(sender=self.__class__, timestamp=self.timestamp, content=self.content, request=self.request)

    def send_client_side_caliper_event(self):
        logger.debug("This is where we'd send the signal to generate a caliper event", self.timestamp, self.content, self.request)
        # client_side_caliper_event.send(sender=self.__class__, timestamp=self.timestamp, content=self.content, request=self.request)