from django.contrib.auth import login
from django.http import JsonResponse
from django.shortcuts import render, redirect

from roster.models import ClusiveUser


def guest_login(request):
    clusive_user = ClusiveUser.make_guest()
    login(request, clusive_user.user)
    return redirect('reader_index')


def set_preference(request, pref, value):
    user = ClusiveUser.from_request(request)
    pref = user.get_preference(pref)
    pref.value = value
    pref.save()
    return JsonResponse({'success' : 1})


def get_preferences(request):
    user = ClusiveUser.from_request(request)
    prefs = user.get_preferences()
    return JsonResponse({p.pref:p.value for p in prefs})