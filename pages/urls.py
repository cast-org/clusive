from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('', TemplateView.as_view(template_name='pages/index.html'), name='index'),
    path('reader/<str:pub_id>', TemplateView.as_view(template_name='pages/reader.html'), name='reader'),
    path('reader', views.reader_index, name='reader_index'),
]