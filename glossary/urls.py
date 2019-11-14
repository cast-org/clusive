from django.urls import path
from . import views

urlpatterns = [
    path('glossdef/<document>/<int:cued>/<word>', views.glossdef, name='glossdef'),
    path('cuelist/<document>', views.cuelist, name='cuelist'),
    path('rating/<word>/<int:rating>', views.set_word_rating, name='set_word_rating'),
    path('rating/<word>', views.get_word_rating, name='get_word_rating'),
]
