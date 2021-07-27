from django.urls import path

from . import views

urlpatterns = [
    path('cta/<cta>', views.CTARedirectView.as_view(), name='take_cta'),
    path('decline/<cta>', views.DeclineCTAView.as_view(), name='decline_cta'),
]
