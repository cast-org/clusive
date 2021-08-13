import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)


class TranslateTextView(LoginRequiredMixin, View):

    def post(self, request):
        text = request.POST.get('text')
        logger.debug("Received a translation request: %s" % text)

        return JsonResponse({'result': 'Translation is not yet implemented.'})
