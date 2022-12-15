import csv
import logging
from datetime import timedelta

from django.contrib import admin
from django.http import StreamingHttpResponse
from django.urls import path, reverse_lazy
from django.views.generic import FormView

from eventlog.forms import EventLogReportForm
from eventlog.models import LoginSession, Event
from library.models import BookVersion
from roster.models import ResearchPermissions

logger = logging.getLogger(__name__)


@admin.register(LoginSession)
class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'user', 'started_at_time', 'ended_at_time', 'active_duration', 'user_agent')
    list_filter= ('user', 'started_at_time')
    list_display = ('id', 'user', 'started_at_time', 'ended_at_time', 'active_duration')
    ordering = ('-started_at_time',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'event_time', 'load_time', 'duration', 'active_duration',
                       'type', 'action',
                       'actor', 'group', 'membership',
                       'book_id', 'book_version_id', 'resource_href', 'resource_progression', 'tip_type',
                       'page', 'control', 'object', 'value',
                       'parent_event_id', 'session', )
    list_display = ('event_time', 'actor', 'type', 'action', 'object', 'page', 'control', 'value',
                    'book_id', 'book_version_id')
    list_filter = ('actor__permission', 'event_time', 'actor', 'control')
    ordering = ('-event_time',)
    change_list_template = 'eventlog/event_changelist.html'

    def group_anon_id(self,obj):
        return obj.group.anon_id if obj.group else None
    group_anon_id.short_description = 'Group'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('download_report_form/', self.admin_site.admin_view(EventLogReportFormView.as_view())),
        ]
        return my_urls + urls


class EventLogReportFormView(FormView):
    template_name = 'eventlog/event_log_report_form.html'
    form_class = EventLogReportForm
    success_url = reverse_lazy('admin:eventlog_event_changelist')

    def form_valid(self, form):
        start_date = form.cleaned_data['start_date']
        # Add a day to end_date since we DO want events that happened on that day, just < the next day.
        end_date = form.cleaned_data['end_date'] + timedelta(days=1)
        logger.debug('Event log query from %s to %s', start_date, end_date)
        events = Event.objects \
            .filter(actor__permission__in=ResearchPermissions.RESEARCHABLE) \
            .filter(event_time__gte=start_date, event_time__lt=end_date) \
            .order_by('event_time') \
            .select_related('actor', 'session', 'group')

        response = StreamingHttpResponse(row_generator(events), content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="event-log.csv"'
        return response

def row_generator(events):
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    yield writer.writerow(['Start Time', 'User', 'Role', 'Permission', 'Period', 'Site',
                           'Type', 'Action', 'Page', 'Control', 'Object', 'Value',
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
            e.type, e.action, e.page, e.control, e.object, e.value,
            info['title'], info['version'], info['owner'],
            duration_s, active_s, e.id, e.session.id, e.book_id, e.book_version_id]


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value
