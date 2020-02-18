from django.urls import path
from django.views.generic import TemplateView, RedirectView

from . import views

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='reader_index'), name='index'),
    path('reader/<str:pub_id>/<int:version>', views.ReaderView.as_view(), name='reader'),
    path('reader/<str:pub_id>', views.ReaderDefaultVersionView.as_view(pattern_name='reader'), name='reader-default'),
    path('reader', views.LibraryView.as_view(), name='reader_index'),
    path('wordbank', views.WordBankView.as_view(), name='word_bank'),
]