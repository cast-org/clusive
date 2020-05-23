from django.urls import path, include
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('login', auth_views.LoginView.as_view(template_name='roster/login.html'), name='login'),
    path('logout', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='roster/password_reset.html',
        email_template_name='roster/password_reset_email.html',
        subject_template_name='roster/password_reset_subject.txt'),
         name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='roster/password_reset_done.html'),
        name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='roster/password_reset_confirm.html',
        post_reset_login=True),
        name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='roster/password_reset_complete.html'),
        name='password_reset_complete'),

    path('guest_login', views.guest_login, name='guest_login'),

    path('prefs', views.get_preferences, name='get_prefs'),
    path('pref/<pref>/<value>', views.set_preference, name='set_pref'),
    path('prefs/reset', views.reset_preferences, name='reset_prefs'),
]