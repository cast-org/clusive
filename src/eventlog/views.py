import csv

from django.contrib.admin.views.decorators import staff_member_required
from django.http import StreamingHttpResponse

from eventlog.models import Event
from roster.models import ResearchPermissions


@staff_member_required
def event_log_report(request):
    # TODO: get actor in same query
    events = Event.objects \
        .filter(actor__permission=ResearchPermissions.PERMISSIONED) \
        .select_related('actor', 'session', 'group')

    response = StreamingHttpResponse(row_generator(events), content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="event-log.csv"'
    return response


def row_generator(events):
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    yield writer.writerow(['Timestamp', 'Event ID', 'Session Id', 'User', 'Role', 'Period',
                           'Type', 'Action', 'Document', 'Page', 'Control', 'Value'])
    for e in events:
        yield writer.writerow(row_for_event(e))


def row_for_event(e):
    period = e.group.anon_id if e.group else None
    return [e.eventTime, e.id, e.session.id, e.actor.anon_id, e.membership, period,
            e.type, e.action, e.document, e.page, e.control, e.value]


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value
