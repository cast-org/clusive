# Create your views here.
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from eventlog.signals import pictures_action
from flaticon.util import FlaticonManager
from library.models import Book
from roster.models import TransformTool


class ShowPicturesView(LoginRequiredMixin, View):

    def post(self, request):
        text = request.POST.get('text')
        lang = 'en'
        book_id = request.POST.get('book_id')
        book = Book.objects.get(pk=book_id) if book_id else None
        clusive_user = request.clusive_user

        clusive_user.set_simplification_tool(TransformTool.PICTURES)

        icon_mgr = FlaticonManager()
        output = icon_mgr.add_pictures(text, clusive_user)

        pictures_action.send(sender=ShowPicturesView.__class__,
                                   request=request,
                                   text=text,
                                   book=book)

        return JsonResponse({'result': output})
