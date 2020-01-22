from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import ListView, TemplateView

from eventlog.signals import page_viewed
from glossary.models import WordModel
from library.models import Book
from roster.models import ClusiveUser


class LibraryView(LoginRequiredMixin,ListView):
    """Library page showing all books"""
    model = Book
    template_name = 'pages/library.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            page_viewed.send(self.__class__, request=request, page='library')
        return super().get(request, *args, **kwargs)


class ReaderView(LoginRequiredMixin,TemplateView):
    """Reader page showing a page of a book"""
    template_name = 'pages/reader.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            context = self.get_context_data(**kwargs)
            pub_id = context.get('pub_id')
            self.extra_context = { 'pub_title' : Book.objects.get(path=pub_id).title}
            page_viewed.send(self.__class__, request=request, document=pub_id)
        return super().get(request, *args, **kwargs)


class WordBankView(LoginRequiredMixin,View):

    def get(self, request, *args, **kwargs):
        clusive_user = get_object_or_404(ClusiveUser, user=request.user)
        context = { 'words': WordModel.objects.filter(user=clusive_user).order_by('word') }
        return render(request, 'pages/wordbank.html', context=context)