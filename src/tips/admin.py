from django.contrib import admin

from tips.models import TipType, TipHistory, CallToAction, CTAHistory


@admin.register(TipType)
class TipTypeAdmin(admin.ModelAdmin):
    model = TipType
    list_display = ('name', 'kind', 'priority', 'max', 'interval',)
    ordering = ('priority',)


@admin.register(TipHistory)
class TipHistoryAdmin(admin.ModelAdmin):
    model = TipHistory
    list_display = ('type', 'user', 'show_count', 'last_attempt', 'last_show', 'last_action',)
    ordering = ('-last_show', 'user',)
    list_filter = ('type', 'user')


@admin.register(CallToAction)
class CallToActionAdmin(admin.ModelAdmin):
    model = CallToAction
    list_display = ('name', 'priority', 'enabled', 'max',)
    ordering = ('priority',)


@admin.register(CTAHistory)
class CTAHistoryAdmin(admin.ModelAdmin):
    model = CTAHistory
    list_display = ('user', 'type', 'show_count', 'first_show', 'last_show', 'completed', 'completion_type',)
    ordering = ('-last_show', 'user',)
