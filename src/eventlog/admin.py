from django.contrib import admin
from django.urls import path

from eventlog import views
from eventlog.models import LoginSession, Event


class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'user', 'startedAtTime', 'endedAtTime', 'userAgent')
    list_filter= ('user', 'startedAtTime')
    list_display = ('id', 'user', 'startedAtTime', 'endedAtTime')
    ordering = ('-startedAtTime',)


class EventAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'eventTime', 'actor', 'group', 'membership', 'parent_event_id', 'type', 'action', 'session',
                       'book_version_id', 'resource_href', 'resource_progression', 'page', 'control', 'value')
    list_display = ('eventTime', 'actor', 'group_anon_id', 'type', 'action', 'page', 'control', 'value',
                    'book_version_id')
    list_filter = ('actor__permission', 'eventTime', 'actor')
    ordering = ('-eventTime',)
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
