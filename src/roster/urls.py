from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView

from . import views

urlpatterns = [
    path('login', LoginView.as_view(template_name='roster/login.html'), name='login'),
    path('logout', LogoutView.as_view(next_page='index'), name='logout'),
    path('guest_login', views.guest_login, name='guest_login'),

    path('prefs', views.get_preferences, name='get_prefs'),
    path('pref/<pref>/<value>', views.set_preference, name='set_pref'),
]