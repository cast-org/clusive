from django.urls import path

from . import views

urlpatterns = [
    path('', views.MessageQueueView.as_view(), name='message_queue'),
]
