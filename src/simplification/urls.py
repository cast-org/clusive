from django.conf.urls import url

from simplification.views import SimplifyTextView, ShowPicturesView, ReportUsageView

urlpatterns = [
    url('simplify', SimplifyTextView.as_view(), name='simplify'),
    url('pictures', ShowPicturesView.as_view(), name='pictures'),
    url('report_usage', ReportUsageView.as_view(), name='report_usage'),
]
