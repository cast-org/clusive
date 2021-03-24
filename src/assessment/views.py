import logging

from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from roster.models import ClusiveUser
from library.models import Book

from .models import ComprehensionCheckResponse


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
        
        clusive_user = ClusiveUser.objects.get(user=self.request.user)
        book = Book.objects.get(id=comprehension_check_data.get("bookId"))

        comprehension_check_response = ComprehensionCheckResponse(
            user = clusive_user,
            book = book,
            comprehension_scale_response = comprehension_check_data.get("scaleResponse"),
            comprehension_free_response = comprehension_check_data.get("freeResponse")
        )

        comprehension_check_response.save()

        return JsonResponse({"success": "1"})        