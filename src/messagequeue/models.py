from enum import Enum

from django.db import models

import django.dispatch

from eventlog.signals import control_used, page_timing

import logging

logger = logging.getLogger(__name__)

client_side_prefs_change = django.dispatch.Signal(providing_args=["timestamp", "content", "request"])

class Message:
    class AllowedTypes(Enum):
        PREF_CHANGE = 'PC'
        CALIPER_EVENT = 'CE'
        PAGE_TIMING = 'PT'

    def __init__(self, message_type, timestamp, content, request):
        # This will raise ValueError if the given type is not in AllowedTypes
        self.type = Message.AllowedTypes(message_type)
        self.timestamp = timestamp 
        self.content = content
        self.request = request

    def send_signal(self):
        if self.type == Message.AllowedTypes.PREF_CHANGE:
            self.send_client_side_prefs_change()
        if self.type == Message.AllowedTypes.CALIPER_EVENT:
            self.send_client_side_caliper_event()
        if self.type == Message.AllowedTypes.PAGE_TIMING:
            self.send_page_timing()

    def send_client_side_prefs_change(self):
        client_side_prefs_change.send(sender=self.__class__, timestamp=self.timestamp, content=self.content, request=self.request)

    def send_client_side_caliper_event(self):    
        event_id = self.content['eventId']  
        control = self.content["caliperEvent"]["control"]
        value = self.content["caliperEvent"]["value"]        
        control_used.send(sender=self.__class__, timestamp=self.timestamp, request=self.request, event_id = event_id, control=control, value=value)

    def send_page_timing(self):
        event_id = self.content['eventId']
        page_timing.send(sender=self.__class__, event_id=event_id, times=self.content)
