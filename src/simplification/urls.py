from django.conf.urls import url

from simplification.views import SimplifyTextView, ShowPicturesView

urlpatterns = [
    url('simplify', SimplifyTextView.as_view(), name='simplify'),
    url('pictures', ShowPicturesView.as_view(), name='pictures'),
]
