from axes.middleware import AxesMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from roster.models import ClusiveUser


class LookupClusiveUserMiddleware:
    """Look up the ClusiveUser (if any) making the request and add it to the request object."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Lookup ClusiveUser before passing control to the view.
        if request.user.is_authenticated:
            try:
                request.clusive_user = ClusiveUser.objects.get(user = request.user)
            except ClusiveUser.DoesNotExist:
                request.clusive_user = None
        else:
            request.clusive_user = None

        response = self.get_response(request)

        # Any postprocessing could be added here.

        return response


class LoginLockoutMiddleware(AxesMiddleware):
    """
    Override default django-axes user lockout handling.
    Get the response provided roster.LoginView, but change its status
    code to 403.
    """

    def __call__(self, request):
        response = self.get_response(request)
        if settings.AXES_ENABLED:
            if getattr(request, "axes_locked_out", None):
                response.status_code = 403
        return response
