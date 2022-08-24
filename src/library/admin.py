import logging

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path

from library.models import Book, BookVersion, Paradata, BookAssignment, Annotation, Subject, ParadataDaily, BookTrend, \
    Customization, CustomVocabularyWord, EducatorResourceCategory
from library.parsing import scan_all_books

logger = logging.getLogger(__name__)


class VersionsInline(admin.StackedInline):
    model = BookVersion
    extra = 0

class SubjectsInline(admin.TabularInline):
    model = Subject
    extra = 1

class subjectBookAdmin(admin.ModelAdmin):
    inlines = (SubjectsInline,)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'resource_identifier', 'title', 'author', 'word_count', 'reading_levels')
    sortable_by = ('id', 'owner', 'resource_identifier', 'title', 'author', 'word_count')
    inlines = [VersionsInline]

    change_list_template = 'library/book_changelist.html'

    def reading_levels(self, book: Book):
        if book.min_reading_level == book.max_reading_level:
            return book.min_reading_level
        else:
            return '%d - %d' % (book.min_reading_level, book.max_reading_level)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('rescan/', self.rescan)
        ]
        return my_urls + urls

    # Define a custom action that scans previously uploaded EPUBs and updates the database
    # This might be useful if database structure or parsing rules get updated
    def rescan(self, request):
        scan_all_books()
        return HttpResponseRedirect("../")


@admin.register(EducatorResourceCategory)
class EducatorResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'sort_order',)
    list_display_links = ('name',)


@admin.register(BookVersion)
class BookVersionAdmin(admin.ModelAdmin):
    list_display = ('book', 'sortOrder', 'reading_level')


@admin.register(BookAssignment)
class BookAssignmentAdmin(admin.ModelAdmin):
    list_display = ('book', 'period', 'date_assigned')
    list_filter = ('book', 'period' )


@admin.register(BookTrend)
class BookTrendAdmin(admin.ModelAdmin):
    list_display = ('book', 'period', 'popularity')
    list_filter = ('book', 'period')


@admin.register(Paradata)
class ParadataAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'view_count', 'last_version', 'last_location')
    sortable_by = ('book', 'user', 'view_count')
    list_filter = ('book', 'user' )


@admin.register(ParadataDaily)
class ParadataDailyAdmin(admin.ModelAdmin):
    list_display = ('paradata', 'date', 'view_count', 'total_time')
    sortable_by = ('paradata__book', 'paradata__user', 'date')


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('user', 'bookVersion', 'dateAdded', 'dateDeleted', 'progression', 'clean_text')
    sortable_by = ('progression', 'user', 'bookVersion', 'dateAdded', 'dateDeleted')
    list_filter = ('bookVersion', 'user' )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['subject', 'sort_order']


@admin.register(Customization)
class CustomizationAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'book', 'title']
    sortable_by = ('id', 'book', 'title')


@admin.register(CustomVocabularyWord)
class CustomVocabularyWordAdmin(admin.ModelAdmin):
    list_display = ['id', 'word', 'customization']
    sortable_by = ('id', 'word', 'customization')
