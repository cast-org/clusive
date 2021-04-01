import logging

from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from roster.models import ClusiveUser
from library.models import Book

from .models import ComprehensionCheck, ComprehensionCheckResponse

from eventlog.signals import comprehension_check_completed

import json

logger = logging.getLogger(__name__)


class ComprehensionCheckView(LoginRequiredMixin, View):
    def post(self, request):            
        try:
            comprehension_check_data = json.loads(request.body)            
            logger.info('Received a valid comprehension check response: %s' % comprehension_check_data)
        except json.JSONDecodeError:
            logger.warning('Received malformed comprehension check data: %s' % request.body)
            return JsonResponse(status=501, data={'message': 'Invalid JSON in request body'})
        
        clusive_user = request.clusive_user
        book = Book.objects.get(id=comprehension_check_data.get("bookId"))

        (ccr, created) = ComprehensionCheckResponse.objects.get_or_create(user = clusive_user, book = book)
        ccr.comprehension_scale_response = comprehension_check_data.get("scaleResponse")
        ccr.comprehension_free_response = comprehension_check_data.get("freeResponse")
        ccr.save()

        # Build event values from comprehension check
        event_value = {ComprehensionCheck.scale_response_key: ccr.comprehension_scale_response,
                       ComprehensionCheck.free_response_key: ccr.comprehension_free_response}

        # Fire event creation signal
        page_event_id = id=comprehension_check_data.get("eventId")        
        comprehension_check_completed.send(sender=self.__class__, 
                          request=self.request, event_id = page_event_id,
                                           comprehension_check_response_id = ccr.id,
                                           value = event_value)

        return JsonResponse({"success": "1"})