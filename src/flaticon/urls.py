from django.conf.urls import url

from flaticon.views import ShowPicturesView

urlpatterns = [
    url('pictures', ShowPicturesView.as_view(), name='pictures'),
]
