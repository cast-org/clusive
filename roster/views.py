from django.contrib.auth import login
from django.shortcuts import render, redirect

from roster.models import ClusiveUser


def guest_login(request):
    clusive_user = ClusiveUser.make_guest()
    login(request, clusive_user.user)
    return redirect('reader_index')
