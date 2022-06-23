from django.contrib import admin

from simplification.models import PictureUsage


@admin.register(PictureUsage)
class PictureUsageAdmin(admin.ModelAdmin):
    list_display = ('date', 'source', 'word', 'icon_id', 'count')

