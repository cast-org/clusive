from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('', TemplateView.as_view(template_name='pages/index.html'), name='index'),
    path('reader/<str:pub_id>', views.ReaderView.as_view(), name='reader'),
    path('reader', views.LibraryView.as_view(), name='reader_index'),
]