import json
import logging
import os

from django.contrib import admin
from django.contrib.staticfiles import finders
from django.http import HttpResponseRedirect
from django.urls import path

from glossary.util import base_form
from library.models import Book, BookVersion, Paradata
from library.parsing import TextExtractor

logger = logging.getLogger(__name__)


class VersionsInline(admin.StackedInline):
    model = BookVersion
    extra = 0


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('path', 'title')
    sortable_by = ('title', 'path')
    inlines = [VersionsInline]

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


@admin.register(BookVersion)
class BookVersionAdmin(admin.ModelAdmin):
    list_display = ('book', 'sortOrder')


@admin.register(Paradata)
class ParadataAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'viewCount', 'lastVersion', 'lastLocation')


def load_static_books():
    pubs_directory = finders.find('shared/pubs')
    book_dirs = os.scandir(pubs_directory)
    for book_dir in book_dirs:
        for version_dir in os.scandir(book_dir):
            if (version_dir.is_dir() and version_dir.name.isnumeric()):
                version = int(version_dir.name)
                # Read the book manifest
                manifestfile = os.path.join(version_dir, 'manifest.json')
                if os.path.exists(manifestfile):
                    with open(manifestfile, 'r') as file:
                        manifest = json.load(file)
                        b, b_created = Book.objects.get_or_create(path=book_dir.name)
                        b.title = find_title(manifest)
                        b.description = find_description(manifest)
                        cover_link = find_cover(manifest)
                        b.cover = version_dir.name + "/" + cover_link if cover_link else None
                        b.save()
                        bv, bv_created = BookVersion.objects.get_or_create(book=b, sortOrder=version)
                        bv.all_word_list = find_all_words(version_dir, manifest)
                        bv.glossary_word_list = find_glossary_words(book_dir, bv.all_word_list)
                        bv.save()
                else:
                    logger.warning("Ignoring directory without manifest: %s", version_dir)
        versions = BookVersion.objects.filter(book__path=book_dir.name)
        # After all versions are read, determine new words added in each version.
        if len(versions)>1:
            for bv in versions:
                if bv.sortOrder > 0:
                    bv.new_word_list = list(set(bv.all_word_list)-set(versions[bv.sortOrder-1].all_word_list))
                    bv.save()


def find_title(manifest):
    title = manifest['metadata'].get('title')
    if not title:
        title = manifest['metadata'].get('headline')
    return title


def find_description(manifest):
    return manifest['metadata'].get('description') or ""


def find_cover(manifest):
    for item in manifest['resources']:
        if item.get('rel') == 'cover':
            return item.get('href')
    return None


def find_glossary_words(book_dir, all_words):
    glossaryfile = os.path.join(book_dir, 'glossary.json')
    if os.path.exists(glossaryfile):
        with open(glossaryfile, 'r', encoding='utf-8') as file:
            glossary = json.load(file)
            words = [base_form(e['headword']) for e in glossary]
            this_version_words = sorted(set(words).intersection(all_words))
            return this_version_words
    else:
        return []


def find_all_words(version_dir, manifest):
    # Look up content files in manifest
    # For each one, gather words
    # Format word set as JSON and return it for storage in database
    te = TextExtractor()
    for file_info in manifest['readingOrder']:
        te.feed_file(os.path.join(version_dir, file_info['href']))
    return sorted(te.get_word_set())
