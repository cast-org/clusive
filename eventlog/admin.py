from django.contrib import admin
from eventlog.models import LoginSession, Event

class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'user', 'startedAtTime', 'endedAtTime', 'userAgent')
    list_filter= ('user', 'startedAtTime')
    list_display = ('id', 'user', 'startedAtTime', 'endedAtTime')
    ordering = ('-startedAtTime',)

class EventAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'eventTime', 'actor', 'group', 'membership', 'type', 'action', 'session', )
    list_display = ('id', 'eventTime', 'actor', 'type', 'action')
    ordering = ('-eventTime',)

admin.site.register(LoginSession, SessionAdmin)
admin.site.register(Event, EventAdmin)
