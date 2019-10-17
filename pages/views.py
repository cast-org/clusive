from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView

from eventlog.signals import page_viewed
from library.models import Book


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
            page_viewed.send(self.__class__, request=request, document=context.get('pub_id'))
        return super().get(request, *args, **kwargs)
