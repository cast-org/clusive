from django.urls import include, path

from authoring.views import LevelingView, SynonymsView

urlpatterns = [
    path('level', LevelingView.as_view(), name='level'),
    path('synonyms/<word>', SynonymsView.as_view(), name='synonyms'),
    ]
