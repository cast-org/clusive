from django.shortcuts import render
from django.http import JsonResponse
from django.views import View

from roster.models import ClusiveUser
from roster.views import set_user_preferences

import json

# Create your views here.


def process_messages(messages, user, request):
    for message in messages:
        message["userId"] = user.id
        if(message["content"]["type"] == 'PC'):
            print("Found a preference change message")
            print(message)
            set_user_preferences(user, message["content"]["preferences"], request)

class MessageQueueView(View):
    def post(self, request):        
        try:
            messages = json.loads(request.body)        
            user = ClusiveUser.from_request(request)
            process_messages(messages, user, request)
        except json.JSONDecodeError:
            return JsonResponse(status=501, data={'message': 'Invalid JSON in request body'})        
        return JsonResponse({'success': messages})