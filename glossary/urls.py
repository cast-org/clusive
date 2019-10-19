from django.urls import path
from . import views

urlpatterns = [
    path('lookup/<word>', views.lookup, name='lookup'),
    path('glossdef/<document>/<word>', views.glossdef, name='glossdef'),
]
