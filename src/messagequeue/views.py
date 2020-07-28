from django.shortcuts import render
from django.http import JsonResponse
from django.views import View

from roster.models import ClusiveUser
from roster.views import set_user_preferences

import json
import logging

import django.dispatch

logger = logging.getLogger(__name__)
 
class MessageProcesser:    
    # Allowed message types
    class MessageTypes:
        PREF_CHANGE = 'PC'

# TODO: replace with Signals-based code?
def process_messages(queue_timestamp, messages, user, request):    
    for message in messages:
        message["content"]["userId"] = user.id
        message_timestamp = message["timestamp"]
        message_content = message["content"]
        message_type = message["content"]["type"]
        if(message_type == MessageProcesser.MessageTypes.PREF_CHANGE):
            logger.debug("Found a preference change message: %s" % message)
            
            set_user_preferences(user, message_content["preferences"], request)

class MessageQueueView(View):
    def post(self, request):        
        try:
            receivedQueue = json.loads(request.body)     
            logger.debug("Received a message queue: %s" % receivedQueue);
            queue_timestamp = receivedQueue["timestamp"]
            messages = receivedQueue["messages"]
            user = request.clusive_user
            process_messages(queue_timestamp, messages, user, request)
        except json.JSONDecodeError:
            return JsonResponse(status=501, data={'message': 'Invalid JSON in request body'})        
        return JsonResponse({'success': 1})