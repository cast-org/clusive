from django.contrib import admin
from django.urls import path

from eventlog import views
from eventlog.models import LoginSession, Event


class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'user', 'started_at_time', 'ended_at_time', 'active_duration', 'user_agent')
    list_filter= ('user', 'started_at_time')
    list_display = ('id', 'user', 'started_at_time', 'ended_at_time', 'active_duration')
    ordering = ('-started_at_time',)


class EventAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'event_time', 'load_time', 'duration', 'active_duration',
                       'type', 'action',
                       'actor', 'group', 'membership',
                       'book_id', 'book_version_id', 'resource_href', 'resource_progression', 'tip_type',
                       'page', 'control', 'object', 'value',
                       'parent_event_id', 'session', )
    list_display = ('event_time', 'actor', 'group_anon_id', 'type', 'action', 'page', 'control', 'value',
                    'book_id', 'book_version_id')
    list_filter = ('actor__permission', 'event_time', 'actor')
    ordering = ('-event_time',)
    change_list_template = 'eventlog/event_changelist.html'

    def group_anon_id(self,obj):
        return obj.group.anon_id if obj.group else None
    group_anon_id.short_description = 'Group'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('download_csv/', views.event_log_report)
        ]
        return my_urls + urls


admin.site.register(LoginSession, SessionAdmin)
admin.site.register(Event, EventAdmin)
