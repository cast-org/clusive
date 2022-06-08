import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from eventlog.signals import simplification_action, pictures_action
from flaticon.util import flaticon_is_configured, FlaticonManager
from library.models import Book
from nounproject.util import NounProjectManager, nounproject_is_configured
from roster.models import TransformTool
from simplification.util import WordnetSimplifier

logger = logging.getLogger(__name__)

class SimplifyTextView(LoginRequiredMixin, View):

    def post(self, request):
        text = request.POST.get('text')
        lang = 'en'
        book_id = request.POST.get('book_id')
        book = Book.objects.get(pk=book_id) if book_id else None
        clusive_user = request.clusive_user

        clusive_user.set_simplification_tool(TransformTool.SIMPLIFY)

        simplification_action.send(sender=SimplifyTextView.__class__,
                                   request=request,
                                   text=text,
                                   book=book)

        simplifier = WordnetSimplifier(lang)
        simplified = simplifier.simplify_text(text, clusive_user=request.clusive_user)

        return JsonResponse({'result': simplified['result']})


class ShowPicturesView(LoginRequiredMixin, View):

    def post(self, request):
        text = request.POST.get('text')
        lang = 'en'
        book_id = request.POST.get('book_id')
        book = Book.objects.get(pk=book_id) if book_id else None
        clusive_user = request.clusive_user

        clusive_user.set_simplification_tool(TransformTool.PICTURES)

        if nounproject_is_configured():
            icon_mgr = NounProjectManager()
        elif flaticon_is_configured():
            icon_mgr = FlaticonManager()
        output = icon_mgr.add_pictures(text, clusive_user)

        pictures_action.send(sender=ShowPicturesView.__class__,
                                   request=request,
                                   text=text,
                                   book=book)

        return JsonResponse({'result': output})
