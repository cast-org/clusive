from django.db import models

import django.dispatch

from eventlog.signals import control_used

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
        control = self.content["caliperEvent"]["control"]
        value = self.content["caliperEvent"]["value"]
        control_used.send(sender=self.__class__, timestamp=self.timestamp, request=self.request, control=control, value=value)        