import csv

from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.shortcuts import render
from django.urls import path

from . import csvparser
from .csvparser import parse_file
from .models import Site, Period, ClusiveUser, Preference, PreferenceSet, UserStats, MailingListMember


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
            path('upload_csv/', upload_csv)
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
    list_display = ('name', 'site', 'id', 'anon_id', 'data_source')


@admin.register(PreferenceSet)
class PreferenceSetAdmin(admin.ModelAdmin):
    model = PreferenceSet


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    model = UserStats
    list_display = ('user', 'logins', 'reading_views', 'active_duration')
    ordering = ('user',)


@admin.register(MailingListMember)
class MailingListMemberAdmin(admin.ModelAdmin):
    model = MailingListMember
    list_display = ('user', 'sync_date')


@staff_member_required
def upload_csv(request):
    template = 'roster/upload_csv.html'
    context = {'fields': csvparser.FIELDS, 'title': 'Bulk add users'}

    if request.method == "GET":
        # First render; just show the form.
        return render(request, template, context)

    # POST means a file was uploaded.
    dry_run = request.POST.get('test')
    if dry_run:
        messages.warning(request, 'Testing CSV file only - database will not be changed')

    if not request.FILES:
        messages.error(request, 'No file uploaded')
    else:
        csv_file = request.FILES['file']
        try:
            csvreader = csv.DictReader(chunk.decode() for chunk in csv_file)
            result = parse_file(csvreader)
            context = result
            context['dry_run'] = dry_run

            if not context['errors'] and not dry_run:
                try:
                    for u in result['users']:
                        ClusiveUser.create_from_properties(u)
                    messages.info(request, 'Users created')
                except Exception as e:
                    context['errors'].append('Database error: %s' % e)
                    messages.error(request, 'Error during creation of users - some may have been created')

        except csv.Error as e:
            context['errors'] = ["CSV formatting error: %s" % e]
            context['sites'] = {}
            context['users'] = {}

        if context['errors']:
            messages.error(request, 'Problems found')
        else:
            messages.info(request, 'File looks good')

    return render(request, template, context)
