import logging

from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

import json

logger = logging.getLogger(__name__)

class ComprehensionCheckView(LoginRequiredMixin, View):
    def post(self, request):            
        try:
            comprehension_check_response = json.loads(request.body)            
            logger.info('Received a valid comprehension check response: %s' % comprehension_check_response)
        except json.JSONDecodeError:
            logger.warning('Received malformed comprehension check data: %s' % request.body)
            return JsonResponse(status=501, data={'message': 'Invalid JSON in request body'})
        # Fill in user id and save            
        return JsonResponse({"foo": "bar"})        