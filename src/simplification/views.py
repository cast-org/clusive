import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from library.models import Book
from simplification.util import WordnetSimplifier

logger = logging.getLogger(__name__)

class SimplifyTextView(LoginRequiredMixin, View):
    def post(self, request):
        text = request.POST.get('text')
        lang = 'en'
        book_id = request.POST.get('book_id')
        book = Book.objects.get(pk=book_id) if book_id else None
        simplifier = WordnetSimplifier(lang)
        simplified = simplifier.simplify_text(text, clusive_user=request.clusive_user)
        logger.debug('simplification input: %s', text)
        logger.debug('simplification output: %s', simplified['result'])
        # translation_action.send(sender=SimplifyTextView.__class__,
        #                         request=request,
        #                         language=lang,
        #                         text=text,
        #                         book=book)

        return JsonResponse({'result': simplified['result']})
