from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.urls import path

from . import views
from .models import Site, Period, ClusiveUser, Preference, PreferenceSet


class ClusiveUserInline(admin.StackedInline):
    model = ClusiveUser
    can_delete = False 
    verbose_name = 'Clusive User Detail'


class UserAdmin(BaseUserAdmin):
    inlines = (ClusiveUserInline,)

    change_list_template = 'roster/user_changelist.html'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('upload_csv/', views.upload_csv)
        ]
        return my_urls + urls


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class PeriodAdminInline(admin.StackedInline):
    model = Period


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    model = Site
    inlines = (PeriodAdminInline,)


@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)
    list_display = ('id', 'user', 'pref', 'value')
    list_filter = ('user', )
    ordering = ('user', 'pref')


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    model = Period

@admin.register(PreferenceSet)
class PreferenceSetAdmin(admin.ModelAdmin):
    model = PreferenceSet

