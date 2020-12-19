from enum import Enum

from django.db import models

import django.dispatch

from eventlog.signals import control_used, page_timing

import logging

from tips.signals import tip_related_action

logger = logging.getLogger(__name__)

client_side_prefs_change = django.dispatch.Signal(providing_args=["timestamp", "content", "request"])

class Message:
    class AllowedTypes(Enum):
        PREF_CHANGE = 'PC'
        CALIPER_EVENT = 'CE'
        PAGE_TIMING = 'PT'
        TIP_RELATED_ACTION = 'TRA'

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
        if self.type == Message.AllowedTypes.TIP_RELATED_ACTION:
            self.send_tip_related_action()

    def send_client_side_prefs_change(self):
        client_side_prefs_change.send(sender=self.__class__, timestamp=self.timestamp, content=self.content, request=self.request)

    def send_client_side_caliper_event(self):    
        event_id = self.content['eventId']  
        event_type = self.content['caliperEvent']['type']
        control = self.content['caliperEvent']['control']
        value = self.content['caliperEvent']['value']
        action = self.content['caliperEvent']['action']
        reader_info = self.content['readerInfo']
        control_used.send(sender=self.__class__, timestamp=self.timestamp,
                          request=self.request, event_id = event_id, event_type=event_type, control=control, value=value, action=action, reader_info=reader_info)

    def send_page_timing(self):
        event_id = self.content['eventId']
        page_timing.send(sender=self.__class__, event_id=event_id, times=self.content)

    def send_tip_related_action(self):
        tip_related_action.send(sender=self.__class__, timestamp=self.timestamp,
                                request=self.request, action=self.content['action'])
