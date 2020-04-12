from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.urls import path

from . import views
from .models import Site, Period, ClusiveUser

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


class PeriodAdminInline(admin.StackedInline):
    model = Period


class SiteAdmin(admin.ModelAdmin):
    model = Site
    inlines = (PeriodAdminInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Site, SiteAdmin)
admin.site.register(Period)