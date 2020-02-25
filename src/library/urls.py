from django.urls import path

from .views import UpdateLastLocationView

urlpatterns = [
    path('setlocation', UpdateLastLocationView.as_view(), name='setlocation')
    ]
