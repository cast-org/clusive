from django.contrib import admin
from eventlog.models import Session, Event

class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'user', 'startedAtTime', 'endedAtTime')
#    list_filter= ('event_id', 'event_time', 'user')

# class EventAdmin(admin.ModelAdmin):
#     readonly_fields = ('id')

admin.site.register(Session, SessionAdmin)
admin.site.register(Event)