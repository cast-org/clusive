from django.urls import path

from . import views

urlpatterns = [
    path('translate', views.TranslateTextView.as_view(), name='translate'),
]
