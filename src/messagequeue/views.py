from django.shortcuts import render
from django.http import JsonResponse
from django.views import View

import json

# Create your views here.

class MessageQueueView(View):
    def post(self, request):
        try:
            messages = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': 0, 'message': 'Invalid JSON in request'})        
        return JsonResponse({'success': 1})
