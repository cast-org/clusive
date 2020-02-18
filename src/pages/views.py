from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import ListView, TemplateView, RedirectView

from eventlog.signals import page_viewed
from glossary.models import WordModel
from library.models import Book, BookVersion
from roster.models import ClusiveUser


class LibraryView(LoginRequiredMixin,ListView):
    """Library page showing all books"""
    model = Book
    template_name = 'pages/library.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            page_viewed.send(self.__class__, request=request, page='library')
        return super().get(request, *args, **kwargs)


class ReaderDefaultVersionView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        kwargs['version'] = 1
        return super().get_redirect_url(*args, **kwargs)


class ReaderView(LoginRequiredMixin,TemplateView):
    """Reader page showing a page of a book"""
    template_name = 'pages/reader.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            context = self.get_context_data(**kwargs)
            pub_id = context.get('pub_id')
            version = int(context.get('version'))
            bv_prev = str(version-1) if version>0 \
                else False
            bv_next = str(version+1) if BookVersion.objects.filter(book__path=pub_id, sortOrder=version+1).exists()\
                else False
            self.extra_context = { 'pub_title' : Book.objects.get(path=pub_id).title,
                                   'prev_version' : bv_prev,
                                   'next_version' : bv_next,
                                   }
            page_viewed.send(self.__class__, request=request, document=pub_id)
        return super().get(request, *args, **kwargs)


class WordBankView(LoginRequiredMixin,View):

    def get(self, request, *args, **kwargs):
        clusive_user = get_object_or_404(ClusiveUser, user=request.user)
        context = { 'words': WordModel.objects.filter(user=clusive_user, interest__gt=0).order_by('word') }
        return render(request, 'pages/wordbank.html', context=context)