from django.views.generic import ListView

from library.models import Book


class LibraryView(ListView):
    """Library page showing all books"""
    model = Book
    template_name = 'pages/library.html'
