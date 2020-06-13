import csv
import logging
import json

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.http import JsonResponse
from django.shortcuts import render, redirect

from django.views import View

from eventlog.signals import preference_changed
from roster import csvparser
from roster.csvparser import parse_file
from roster.models import ClusiveUser, Site, Period, PreferenceSet

logger = logging.getLogger(__name__)

def guest_login(request):
    clusive_user = ClusiveUser.make_guest()
    login(request, clusive_user.user)
    return redirect('reader_index')


class PreferenceView(View):

    def get(self, request):
        user = ClusiveUser.from_request(request)
        return JsonResponse(user.get_preferences_dict())

    def post(self, request):
        try:
            request_prefs = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': 0, 'message': 'Invalid JSON in request'})

        user = ClusiveUser.from_request(request)        
        set_user_preferences(user, request_prefs, request)

        return JsonResponse({'success': 1})


# TODO: should we specially log an event that adopts a full new preference set?
class PreferenceSetView(View):

    def post(self, request):
        user = ClusiveUser.from_request(request)
        try:
            request_json = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': 0, 'message': 'Invalid JSON in request'})            
        
        desired_prefs_name = request_json["adopt"]
        
        try:
            desired_prefs = PreferenceSet.get_json(desired_prefs_name)
        except PreferenceSet.DoesNotExist:
            return JsonResponse({'success': 0, 'message': 'Preference set named %s does not exist' % desired_prefs_name })

        # Replace all existing preferences with the new set.
        # user.delete_preferences()
        set_user_preferences(user, desired_prefs, request)

        # Return the newly-established preferences
        return JsonResponse(user.get_preferences_dict())


# Set user preferences from a dictionary
def set_user_preferences(user, new_prefs, request):
    """Sets User's preferences to match the given dictionary of preference values.
    Any preferences NOT specified in the dictionary are set to their default values."""
    old_prefs = user.get_preferences_dict()
    prefs_to_use = PreferenceSet.get_json('default')
    prefs_to_use.update(new_prefs)
    for pref_key in prefs_to_use:
        old_val = old_prefs.get(pref_key)
        if old_val != prefs_to_use[pref_key]:
            pref = user.set_preference(pref_key, prefs_to_use[pref_key])
            # logger.debug("Pref %s changed %s (%s) -> %s (%s)", pref_key,
            #              old_val, type(old_val),
            #              pref.typed_value, type(pref.typed_value))
            preference_changed.send(sender=ClusiveUser.__class__, request=request, preference=pref)


@staff_member_required
def upload_csv(request):
    template = 'roster/upload_csv.html'
    context = {'fields' : csvparser.FIELDS, 'title': 'Bulk add users' }

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
            context['errors'] = ["CSV formatting error: %s" % e ]
            context['sites'] = {}
            context['users'] = {}

        if context['errors']:
            messages.error(request, 'Problems found')
        else:
            messages.info(request, 'File looks good')

    return render(request, template, context)
