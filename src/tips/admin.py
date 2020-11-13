from django.contrib import admin

from tips.models import TipType, TipHistory


@admin.register(TipType)
class TipTypeAdmin(admin.ModelAdmin):
    model = TipType
    list_display = ('priority', 'name', 'max', 'interval')
    ordering = ('priority',)


@admin.register(TipHistory)
class TipTypeAdmin(admin.ModelAdmin):
    model = TipHistory
    list_display = ('user', 'type', 'show_count', 'last_show', 'last_action')
    ordering = ('user',)
