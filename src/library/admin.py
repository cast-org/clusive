import json
import logging
import os

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path

from glossary.util import base_form
from library.models import Book, BookVersion, Paradata, BookAssignment, Annotation
from library.parsing import TextExtractor, scan_all_books

logger = logging.getLogger(__name__)


class VersionsInline(admin.StackedInline):
    model = BookVersion
    extra = 0


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'title', 'author')
    sortable_by = ('id', 'owner', 'title', 'author')
    inlines = [VersionsInline]

    change_list_template = 'library/book_changelist.html'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('rescan/', self.rescan)
        ]
        return my_urls + urls

    ## Define a custom action that scans previously uploaded EPUBs and updates the database
    ## This might be useful if database structure or parsing rules get updated
    def rescan(self, request):
        scan_all_books()
        return HttpResponseRedirect("../")


@admin.register(BookVersion)
class BookVersionAdmin(admin.ModelAdmin):
    list_display = ('book', 'sortOrder')


@admin.register(BookAssignment)
class BookAssignmentAdmin(admin.ModelAdmin):
    list_display = ('book', 'period', 'dateAssigned')
    list_filter = ('book', 'period' )


@admin.register(Paradata)
class ParadataAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'viewCount', 'lastVersion', 'lastLocation')
    sortable_by = ('book', 'user', 'viewCount')
    list_filter = ('book', 'user' )


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('user', 'bookVersion', 'dateAdded', 'dateDeleted', 'progression', 'clean_text')
    sortable_by = ('progression', 'user', 'bookVersion', 'dateAdded', 'dateDeleted')
    list_filter = ('bookVersion', 'user' )
