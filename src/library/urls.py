from django.urls import path

from .views import UpdateLastLocationView, AnnotationView

urlpatterns = [
    path('setlocation', UpdateLastLocationView.as_view(), name='setlocation'),
    path('annotation', AnnotationView.as_view(), name='annotation'),
]
