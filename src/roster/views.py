from django.contrib.auth import login
from django.http import JsonResponse
from django.shortcuts import render, redirect

from eventlog.signals import preference_changed
from roster.models import ClusiveUser


def guest_login(request):
    clusive_user = ClusiveUser.make_guest()
    login(request, clusive_user.user)
    return redirect('reader_index')


def set_preference(request, pref, value):
    user = ClusiveUser.from_request(request)
    preference = user.get_preference(pref)
    preference.value = value
    preference.save()
    preference_changed.send(sender=ClusiveUser.__class__, request=request, preference=preference)
    return JsonResponse({'success' : 1})


def get_preferences(request):
    user = ClusiveUser.from_request(request)
    prefs = user.get_preferences()
    return JsonResponse({p.pref:p.value for p in prefs})

def reset_preferences(request):
    user = ClusiveUser.from_request(request)    
    user.delete_preferences()
    return JsonResponse({'success': 1})
