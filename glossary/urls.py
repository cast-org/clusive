from django.urls import path
from . import views

urlpatterns = [
    path('glossdef/<document>/<int:cued>/<word>', views.glossdef, name='glossdef'),
    path('cuelist/<document>', views.cuelist, name='cuelist'),
]
