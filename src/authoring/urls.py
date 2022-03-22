from django.urls import path

from authoring.views import LevelingView, SynonymsView, BookInfoView, SimplifyView

urlpatterns = [
    path('level', LevelingView.as_view(), name='level'),
    path('simplify', SimplifyView.as_view(), name='simplify'),
    path('synonyms/<word>', SynonymsView.as_view(), name='synonyms'),
    path('info', BookInfoView.as_view(), name='book_info'),
    ]
