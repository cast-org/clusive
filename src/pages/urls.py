from django.urls import path
from django.views.generic import TemplateView, RedirectView

from . import views

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='reader_index'), name='index'),
    path('reader', views.ReaderIndexView.as_view(), name='reader_index'),
    path('reader/<int:book_id>/<int:version>', views.ReaderView.as_view(), name='reader'),
    path('reader/<int:book_id>', views.ReaderChooseVersionView.as_view(pattern_name='reader'), name='reader-default'),
    path('wordbank', views.WordBankView.as_view(), name='word_bank'),
]