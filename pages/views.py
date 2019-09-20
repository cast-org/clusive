from django.http import HttpResponse
from django.shortcuts import render

from django.contrib.staticfiles import finders
from os import listdir

# builds an index of available publications by scanning the 'shared/pubs' directory

def reader_index(request):
    pubs_directory = finders.find('shared/pubs')
    pub_directory_names = listdir(pubs_directory)
    return render(request, 'pages/reader_index.html', context={'pubs': pub_directory_names})