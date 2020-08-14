from django.urls import include, path

from authoring.views import LevelingView

urlpatterns = [
    path('level', LevelingView.as_view(), name='level'),
    ]
