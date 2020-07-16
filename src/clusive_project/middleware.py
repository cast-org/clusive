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
