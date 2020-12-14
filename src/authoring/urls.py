from django.urls import include, path

from authoring.views import LevelingView, SynonymsView, BookInfoView

urlpatterns = [
    path('level', LevelingView.as_view(), name='level'),
    path('synonyms/<word>', SynonymsView.as_view(), name='synonyms'),
    path('info', BookInfoView.as_view(), name='book_info'),
    ]
