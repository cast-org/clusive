from django.contrib import admin
from assessment.models import AffectiveCheckResponse, ComprehensionCheckResponse

admin.site.register(ComprehensionCheckResponse)
admin.site.register(AffectiveCheckResponse)