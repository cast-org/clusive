from django.contrib import admin
from django.urls import path

from eventlog import views
from eventlog.models import LoginSession, Event
from roster.models import Preference


class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'user', 'startedAtTime', 'endedAtTime', 'userAgent')
    list_filter= ('user', 'startedAtTime')
    list_display = ('id', 'user', 'startedAtTime', 'endedAtTime')
    ordering = ('-startedAtTime',)


class EventAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'eventTime', 'actor', 'group', 'membership', 'type', 'action', 'session',
                       'document', 'document_version', 'document_href', 'document_progression', 'page', 'control', 'value')
    list_display = ('eventTime', 'actor', 'group', 'type', 'action', 'value')
    list_filter = ('actor__permission', 'eventTime')
    ordering = ('-eventTime',)
    change_list_template = 'eventlog/event_changelist.html'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('download_csv/', views.event_log_report)
        ]
        return my_urls + urls


admin.site.register(LoginSession, SessionAdmin)
admin.site.register(Event, EventAdmin)
