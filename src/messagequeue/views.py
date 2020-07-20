from django.shortcuts import render
from django.http import JsonResponse
from django.views import View

import json

# Create your views here.

class MessageQueueView(View):
    def post(self, request):        
        try:
            messages = json.loads(request.body)        
            print(messages)
        except json.JSONDecodeError:
            return JsonResponse(status=501, data={'message': 'Invalid JSON in request body'})        
        return JsonResponse({'success': messages})
