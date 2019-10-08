from django.urls import path
from . import views

urlpatterns = [
    path('lookup/<word>', views.lookup, name='lookup'),
    path('glossdef/<word>', views.glossdef, name='glossdef'),
]
