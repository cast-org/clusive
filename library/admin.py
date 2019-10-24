import json
import logging
import os

from django.contrib import admin
from django.contrib.staticfiles import finders
from django.http import HttpResponseRedirect
from django.urls import path

from library.models import Book
from library.parsing import TextExtractor

logger = logging.getLogger(__name__)


class BookAdmin(admin.ModelAdmin):
    list_display = ('path', 'title')
    sortable_by = ('title', 'path')
    change_list_template = 'library/book_changelist.html'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('rescan/', self.rescan)
        ]
        return my_urls + urls

    ## Define a custom action that scans the EPUBs in the static files and updates the database
    def rescan(self, request):
        load_static_books()
        return HttpResponseRedirect("../")


admin.site.register(Book, BookAdmin)


def load_static_books():
    pubs_directory = finders.find('shared/pubs')
    book_dirs = os.scandir(pubs_directory)
    for book_dir in book_dirs:
        # Read the book manifest
        manifestfile = os.path.join(book_dir, 'manifest.json')
        if os.path.exists(manifestfile):
            with open(manifestfile, 'r') as file:
                b, created = Book.objects.get_or_create(path=book_dir.name)
                manifest = json.load(file)
                b.title = find_title(manifest)
                b.cover = find_cover(manifest)
                b.glossary_words = find_glossary_words(book_dir)
                b.all_words = find_all_words(book_dir, manifest)
                b.save()
        else:
            logger.warning("Ignoring directory without manifest: %s", book_dir)


def find_title(manifest):
    title = manifest['metadata'].get('title')
    if not title:
        title = manifest['metadata'].get('headline')
    return title


def find_cover(manifest):
    for item in manifest['resources']:
        if item.get('rel') == 'cover':
            return item.get('href')
    return None


def find_glossary_words(book_dir):
    glossaryfile = os.path.join(book_dir, 'glossary.json')
    if os.path.exists(glossaryfile):
        with open(glossaryfile, 'r') as file:
            glossary = json.load(file)
            words = [e['headword'] for e in glossary]
            return json.dumps(words)
    else:
        return "[]"


def find_all_words(book_dir, manifest):
    # Look up content files in manifest
    # For each one, gather words
    # Format word set as JSON and return it for storage in database
    te = TextExtractor()
    for file_info in manifest['readingOrder']:
        te.feed_file(os.path.join(book_dir, file_info['href']))
    return json.dumps(sorted(te.get_word_set()))

