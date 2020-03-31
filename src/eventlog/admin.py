from django.contrib import admin
from eventlog.models import LoginSession, Event
from roster.models import Preference


class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'user', 'startedAtTime', 'endedAtTime', 'userAgent')
    list_filter= ('user', 'startedAtTime')
    list_display = ('id', 'user', 'startedAtTime', 'endedAtTime')
    ordering = ('-startedAtTime',)


class EventAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'eventTime', 'actor', 'group', 'membership', 'type', 'action', 'session',
                       'document', 'page', 'control', 'value')
    list_display = ('id', 'eventTime', 'actor', 'type', 'action')
    ordering = ('-eventTime',)


class PreferenceAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)
    list_display = ('id', 'user', 'pref', 'value')
    ordering = ('user', 'pref')


admin.site.register(LoginSession, SessionAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Preference, PreferenceAdmin)
