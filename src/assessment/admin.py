from django.contrib import admin
from assessment.models import AffectiveCheckResponse, ComprehensionCheckResponse, ClusiveRatingResponse


@admin.register(AffectiveCheckResponse)
class AffectiveCheckResponseAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'created', 'updated')
    list_display = ('updated', 'user', 'book')
    ordering = ('-updated',)


@admin.register(ComprehensionCheckResponse)
class ComprehensionCheckResponseAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'created', 'updated')
    list_display = ('updated', 'user', 'book', 'comprehension_scale_response')
    ordering = ('-updated',)

@admin.register(ClusiveRatingResponse)
class ClusiveRatingResponseAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'created')
    list_display = ('user', 'star_rating', 'created',)
    ordering = ('-created',)
