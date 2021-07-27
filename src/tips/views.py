import logging

from django.urls import reverse, reverse_lazy
from django.views.generic import RedirectView

from tips.models import CTAHistory, CompletionType

logger = logging.getLogger(__name__)


class CTARedirectView(RedirectView):
    """Marks a CTA as TAKEN and redirects the user to an appropriate destination, eg a survey page."""

    def get(self, request, *args, **kwargs):
        self.cta = kwargs['cta']
        CTAHistory.register_action(user=request.clusive_user, cta_name=self.cta, completion_type=CompletionType.TAKEN)
        return super().get(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        logger.debug('Heeded CTA: %s', self.cta)
        if self.cta == 'summer_reading_st':
            # TODO: survey should accept anon_id
            return 'https://sri.co1.qualtrics.com/jfe/form/SV_b49OZCdvuAWpy8S'
        elif self.cta == 'summer_reading_gu':
            return reverse('sign_up_role')
        else:
            return reverse('dashboard')


class DeclineCTAView(RedirectView):
    url = reverse_lazy('dashboard')

    def get(self, request, *args, **kwargs):
        cta = kwargs['cta']
        CTAHistory.register_action(user=request.clusive_user, cta_name=cta, completion_type=CompletionType.DECLINED)
        logger.debug('Declined CTA: %s', cta)
        return super().get(request, *args, **kwargs)
