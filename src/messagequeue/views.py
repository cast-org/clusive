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
        message["content"]["userId"] = user.id
        message_timestamp = message["timestamp"]
        message_time = dateutil_parse(message_timestamp)
        adjusted_message_time = message_time+delta
        message_timestamp = adjusted_message_time.isoformat()
        logger.debug("Adjusted message time from %s to %s" % (message_time, adjusted_message_time))
        message_content = message["content"]
        
        message_type = message["content"]["type"]
        if(message_type == Message.AllowedTypes.PREF_CHANGE):
            logger.debug("Found a preference change message: %s" % message)                        
            message = Message(message_type, message_timestamp, message_content, request)            

def get_delta_from_now(compare_time):
    now = timezone.now()
    return relativedelta(now, compare_time)

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