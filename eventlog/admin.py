from django.contrib import admin
from eventlog.models import Session, Event

class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'user', 'startedAtTime', 'endedAtTime')
    list_filter= ('user', 'startedAtTime')
    ordering = ('-startedAtTime',)

class EventAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'session')
    ordering = ('-eventTime',)

admin.site.register(Session, SessionAdmin)
admin.site.register(Event, EventAdmin)
