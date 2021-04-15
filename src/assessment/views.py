import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from eventlog.signals import assessment_completed
from library.models import Book
from .models import ComprehensionCheck, ComprehensionCheckResponse

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

        (ccr, created) = ComprehensionCheckResponse.objects.get_or_create(user=clusive_user, book=book)
        ccr.comprehension_scale_response = comprehension_check_data.get('scaleResponse')
        ccr.comprehension_free_response = comprehension_check_data.get('freeResponse')
        ccr.save()

        # Fire event creation signals
        page_event_id =comprehension_check_data.get("eventId")
        assessment_completed.send(sender=self.__class__,
                                  request=self.request, event_id=page_event_id,
                                  comprehension_check_response_id=ccr.id,
                                  key=ComprehensionCheck.scale_response_key,
                                  question=comprehension_check_data.get('scaleQuestion'),
                                  answer=ccr.comprehension_scale_response)
        assessment_completed.send(sender=self.__class__,
                                  request=self.request, event_id=page_event_id,
                                  comprehension_check_response_id=ccr.id,
                                  key=ComprehensionCheck.free_response_key,
                                  question=comprehension_check_data.get('freeQuestion'),
                                  answer=ccr.comprehension_free_response)

        return JsonResponse({"success": "1"})

    def get(self, request, book_id):
        user = request.clusive_user
        book = Book.objects.get(id=book_id)        
        ccr = get_object_or_404(ComprehensionCheckResponse, user=user, book=book)            
        response_value = {ComprehensionCheck.scale_response_key: ccr.comprehension_scale_response,
                       ComprehensionCheck.free_response_key: ccr.comprehension_free_response}
        return JsonResponse(response_value)