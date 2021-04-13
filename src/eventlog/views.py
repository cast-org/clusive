import csv
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import StreamingHttpResponse
from django.views.generic.base import ContextMixin

from eventlog.models import Event
from library.models import BookVersion
from roster.models import ResearchPermissions

logger = logging.getLogger(__name__)

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
        raise NotImplementedError('View must define the contribute_event_data method')


@staff_member_required
def event_log_report(request):
    # TODO: get actor in same query
    events = Event.objects \
        .filter(actor__permission__in=ResearchPermissions.RESEARCHABLE) \
        .select_related('actor', 'session', 'group')

    response = StreamingHttpResponse(row_generator(events), content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="event-log.csv"'
    return response


def row_generator(events):
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    yield writer.writerow(['Start Time', 'User', 'Role', 'Permission', 'Period', 'Site',
                           'Type', 'Action', 'Page', 'Control', 'Value',
                           'Book Title', 'Book Version', 'Book Owner',
                           'Duration', 'Active Duration',
                           'Event ID', 'Session ID', 'Book ID', 'Book Version ID'])
    period_site = {}
    book_info = {}
    for e in events:
        yield writer.writerow(row_for_event(e, period_site, book_info))


def row_for_event(e: Event, period_site, book_info):
    period = e.group.anon_id if e.group else None
    # period_site map caches lookups of the site anon_id for each period.
    if period:
        site = period_site.get(period)
        if not site:
            site = e.group.site.anon_id
            period_site[period] = site
    else:
        site = None
    if e.book_version_id:
        info = book_info.get(e.book_version_id)
        if not info:
            try:
                bv: BookVersion
                bv = BookVersion.objects.get(id=e.book_version_id)
                info = {
                    'title': bv.book.title,
                    'version': bv.sortOrder,
                    'owner': bv.book.owner.anon_id if bv.book.owner else None
                }
            except BookVersion.DoesNotExist:
                info = {
                    'title': '[deleted]',
                    'version': None,
                    'owner': None
                }
            book_info[e.book_version_id] = info
    else:
        info = {
            'title': None,
            'version': None,
            'owner': None
        }
    duration_s = e.duration.total_seconds() if e.duration else ''
    active_s = e.active_duration.total_seconds() if e.active_duration else ''
    return [e.event_time, e.actor.anon_id, e.membership, e.actor.permission, period, site,
            e.type, e.action, e.page, e.control, e.value,
            info['title'], info['version'], info['owner'],
            duration_s, active_s, e.id, e.session.id, e.book_id, e.book_version_id]


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value
