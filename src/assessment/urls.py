from django.urls import path

from . import views

urlpatterns = [
    path('comprehension_check', views.ComprehensionCheckView.as_view(), name='comprehension_check')
]