from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import ClusiveUser

class ClusiveUserInline(admin.StackedInline):
    model = ClusiveUser
    can_delete = False 
    verbose_name = 'Clusive User Detail'

class UserAdmin(BaseUserAdmin):
    inlines = (ClusiveUserInline,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)