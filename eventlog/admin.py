from django.contrib import admin
from eventlog.models import Session, Event

class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'user', 'startedAtTime', 'endedAtTime')
    list_filter= ('user', 'startedAtTime')
    list_display = ('id', 'user', 'startedAtTime', 'endedAtTime')
    ordering = ('-startedAtTime',)

class EventAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'session', 'actor', 'eventTime', 'type', 'action')
    list_display = ('id', 'eventTime', 'actor', 'type', 'action')
    ordering = ('-eventTime',)

admin.site.register(Session, SessionAdmin)
admin.site.register(Event, EventAdmin)
