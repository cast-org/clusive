from django.shortcuts import render
from django.http import JsonResponse
from django.views import View

from roster.models import ClusiveUser
from roster.views import set_user_preferences

from django.utils import timezone

from dateutil.parser import parse as dateutil_parse
from dateutil.relativedelta import relativedelta


from .models import Message

import json
import logging

logger = logging.getLogger(__name__)

def process_messages(queue_timestamp, messages, user, request):    
    client_reported_time = dateutil_parse(queue_timestamp)    
    delta = get_delta_from_now(client_reported_time)    

    for message in messages:
        message_username = message["username"]
        session_username = user.username
        if(message_username != session_username):
            logger.debug("Rejected individual message, message username %s did not match session username %s ",
                         message_username, session_username)
            break
        message_timestamp = adjust_message_timestamp(message["timestamp"], delta)        
        message_content = message["content"]
        
        message_type = message["content"]["type"]
        new_message = None
        
        if(message_type == Message.AllowedTypes.PREF_CHANGE):
            logger.debug("Found a preference change message: %s" % message)                        
            new_message = Message(message_type, message_timestamp, message_content, request)
        elif(message_type == Message.AllowedTypes.CALIPER_EVENT):
            logger.debug("Found a Caliper event message: %s" % message)
            new_message = Message(message_type, message_timestamp, message_content, request)
        try:            
            new_message.send_signal()            
        except AttributeError:
            logger.debug("Message type %s is not a valid type" % message_type)

def adjust_message_timestamp(timestamp, delta):
    message_time = dateutil_parse(timestamp)
    adjusted_message_time = message_time+delta
    message_timestamp = adjusted_message_time.isoformat()
    return message_timestamp

def get_delta_from_now(compare_time):
    now = timezone.now()
    return relativedelta(now, compare_time)

class MessageQueueView(View):
    def post(self, request):        
        try:
            receivedQueue = json.loads(request.body)     
            logger.debug("Received a message queue: %s" % receivedQueue)
            queue_timestamp = receivedQueue["timestamp"]
            queue_username = receivedQueue["username"]
            messages = receivedQueue["messages"]
            clusive_user = request.clusive_user
            print(clusive_user)
            username = clusive_user.user.username
            if(queue_username == username):
                process_messages(queue_timestamp, messages, clusive_user.user, request)
            else: 
                logger.debug("Rejected message queue, queue username %s did not match session username %s ",
                             queue_username, username)
                return JsonResponse(status=501, data={'message': 'Invalid user'})            
        except json.JSONDecodeError:
            return JsonResponse(status=501, data={'message': 'Invalid JSON in request body'})        
        return JsonResponse({'success': 1})