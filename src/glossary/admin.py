from django.contrib import admin

from glossary.models import WordModel


@admin.register(WordModel)
class WordModelAdmin(admin.ModelAdmin):
    list_display = ('user', 'word', 'rating', 'cued')
