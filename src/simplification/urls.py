from django.conf.urls import url

from simplification.views import SimplifyTextView

urlpatterns = [
    url('simplify', SimplifyTextView.as_view(), name='simplify'),
]
