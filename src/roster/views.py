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
        prefs = user.get_preferences()
        return JsonResponse({p.pref:p.value for p in prefs})
    def post(self, request):        
        try:
            request_prefs = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': 0, 'message': 'Invalid JSON in request'})

        user = ClusiveUser.from_request(request)        
        set_user_preferences(user, request_prefs, request)
        for req_pref_key in request_prefs:
            req_pref_val = request_prefs[req_pref_key]
            preference = user.get_preference(req_pref_key)               
            if(preference.value != req_pref_val):                           
                preference.value = req_pref_val
                preference.save()
                preference_changed.send(sender=ClusiveUser.__class__, request=request, preference=preference)            

        return JsonResponse({'success': 1})

# TODO: should we specially log an event that adopts a full new preference set?
class PreferenceSetView(View):
    def post(self, request):
        user = ClusiveUser.from_request(request)
        try:
            request_json = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': 0, 'message': 'Invalid JSON in request'})            
        
        desired_prefs_set_name = request_json["adopt"]
        
        try:
            prefs_set = PreferenceSet.objects.get(set_name=desired_prefs_set_name)
        except PreferenceSet.DoesNotExist:
            return JsonResponse({'success': 0, 'message': 'Preference set named %s does not exist' % desired_prefs_set_name })            

        desired_prefs = json.loads(prefs_set.prefs_json)

        # Clear existing preferences
        user.delete_preferences()

        set_user_preferences(user, desired_prefs, request)

        prefs = user.get_preferences()
        return JsonResponse({p.pref:p.value for p in prefs})

# Return a JSON object from a set of user preferences
# Casts numbers-as-strings and booleans-as-strings as appropriate

# Set user preferences from a dictionary
def set_user_preferences(user, new_prefs, request):
    for pref_key in new_prefs:
            pref_val = new_prefs[pref_key]
            preference = user.get_preference(pref_key)               
            if(preference.value != pref_val):                           
                preference.value = pref_val
                preference.save()
                preference_changed.send(sender=ClusiveUser.__class__, request=request, preference=preference)            

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
