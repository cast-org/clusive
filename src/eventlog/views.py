import logging

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic.base import ContextMixin

from eventlog.models import Event

logger = logging.getLogger(__name__)

# All views using EventMixin should never browser cache, so that
# statistics are accurate
@method_decorator(never_cache, name='get')
class EventMixin(ContextMixin):
    """
    Creates a VIEW_EVENT for this view, and includes the event ID in the context for client-side use.
    Views that use this mixin must define a configure_event method to add appropriate data fields to the event.
    They must also call the super() methods in their get(...) and get_context_data() methods.
    """

    def get(self, request, *args, **kwargs):
        # Create Event first since Event ID is used during page construction
        # Note, if no user is logged in this will return None.
        event = Event.build(type='VIEW_EVENT',
                            action='VIEWED',
                            session=request.session)
        if event:
            self.event_id = event.id
        # Super will create the page as normal
        result = super().get(request, *args, **kwargs)
        if event:
            self.event_id = event.id
            # Configure_event is run last so it can use any info generated during page construction.
            self.configure_event(event)
            event.save()
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['event_id'] = self.event_id
        except AttributeError:
            logger.warning('event_id missing from page view.')
        return context

    def configure_event(self, event: Event):
        raise NotImplementedError('View must define the configure_event method')
