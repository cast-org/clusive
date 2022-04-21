from django.urls import path

from . import views

urlpatterns = [
    path('', views.MessageQueueView.as_view(), name='message_queue'),
    path('<str:event_id>/', views.MessageQueueView.as_view(), name='message_queue'),
]
