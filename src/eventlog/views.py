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
    yield writer.writerow(['Timestamp', 'User', 'Role', 'Period', 'Site',
                           'Type', 'Action', 'Document', 'Page', 'Control', 'Value',
                           'Event ID', 'Session Id'])
    period_site = {}
    for e in events:
        yield writer.writerow(row_for_event(e, period_site))


def row_for_event(e, period_site):
    period = e.group.anon_id if e.group else None
    # period_site map caches lookups of the site anon_id for each period.
    if period:
        site = period_site.get(period)
        if not site:
            site = e.group.site.anon_id
            period_site[period] = site
    else:
        site = None
    return [e.eventTime, e.actor.anon_id, e.membership, period, site,
            e.type, e.action, e.document, e.page, e.control, e.value,
            e.id, e.session.id]


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value
