from django.shortcuts import render
from django.http import JsonResponse
from django.views import View

from roster.models import ClusiveUser
from roster.views import set_user_preferences

import json
import logging

logger = logging.getLogger(__name__)

# Create your views here.

# TODO: this needs to be replaced with something that actually works with the Model 
# definition and the signals code
def process_messages(messages, user, request):
    for message in messages:
        message["userId"] = user.id
        if(message["content"]["type"] == 'PC'):
            logger.debug("Found a preference change message: %s" % message)
            
            set_user_preferences(user, message["content"]["preferences"], request)

class MessageQueueView(View):
    def post(self, request):        
        try:
            receivedQueue = json.loads(request.body)     
            logger.debug("Received a message queue: %s" % receivedQueue);
            messages = receivedQueue["messages"]
            user = ClusiveUser.from_request(request)
            process_messages(messages, user, request)
        except json.JSONDecodeError:
            return JsonResponse(status=501, data={'message': 'Invalid JSON in request body'})        
        return JsonResponse({'success': messages})