from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('login', views.LoginView.as_view(), name='login'),
    path('logout', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='roster/password_change.html'),
         name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='roster/password_change_done.html'),
         name='password_change_done'),
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
        post_reset_login=True,
        post_reset_login_backend='django.contrib.auth.backends.ModelBackend'),
         name='password_reset_confirm'),
    path('reset/done/', views.PasswordResetResetLockoutView.as_view(
        template_name='roster/password_reset_complete.html'),
         name='password_reset_complete'),

    path('guest_login', views.guest_login, name='guest_login'),

    path('sign_up_role', views.SignUpRoleView.as_view(), name='sign_up_role'),
    path('sign_up_age', views.SignUpAgeCheckView.as_view(), name='sign_up_age_check'),
    path('sign_up_ask_parent', views.SignUpAskParentView.as_view(), name='sign_up_ask_parent'),
    path('sign_up/<role>/<isSSO>', views.SignUpView.as_view(), name='sign_up'),

    path('validate_sent/<int:user_id>', views.ValidateSentView.as_view(), name='validate_sent'),
    path('validate_resend/<int:user_id>', views.ValidateResendView.as_view(), name='validate_resend'),
    path('validate/<int:user_id>/<token>', views.ValidateEmailView.as_view(), name='validate'),

    path('prefs', views.PreferenceView.as_view(), name='prefs'),
    path('prefs/profile', views.PreferenceSetView.as_view(), name='prefs_profile'),

    path('manage/<int:period_id>', views.ManageView.as_view(), name='manage'),
    path('manage', views.ManageView.as_view(), name='manage'),

    path('manage_edit/<int:period_id>/<int:pk>', views.ManageEditUserView.as_view(), name='manage_edit'),
    path('manage_create_user/<int:period_id>/', views.ManageCreateUserView.as_view(), name='manage_create_user'),
    path('manage_edit_period/<int:pk>', views.ManageEditPeriodView.as_view(), name='manage_edit_period'),
    path('manage_create_period/', views.ManageCreatePeriodView.as_view(), name='manage_create_period'),
    path('finish_login', views.finish_login, name='finish_login'),
    path('cancel_registration', views.cancel_registration, name='cancel_registration'),
    path('get_google_courses', views.GetGoogleCourses.as_view(), name='get_google_courses'),
    path('manage_google_courses', views.GoogleCoursesView.as_view(), name='manage_google_courses'),
    path('manage_google_roster/<course_id>', views.GoogleRosterView.as_view(), name='manage_google_roster'),
    path('google_roster_sync/<course_id>/<int:period_id>', views.GoogleRosterSyncView.as_view(), name='google_roster_sync'),
    path('google_roster_update/<course_id>/<int:period_id>', views.GooglePeriodRosterUpdate.as_view(), name='google_roster_update'),
    path('get_google_roster/<course_id>', views.GetGoogleRoster.as_view(), name='get_google_roster'),
    path('get_google_roster/<course_id>/<int:period_id>', views.GetGoogleRoster.as_view(), name='get_google_roster'),
    path('google_import_confirm/<course_id>', views.GooglePeriodImport.as_view(), name='google_import_confirm'),
    path('add_scope_access', views.add_scope_access, name='add_scope_access'),
    path('add_scope_callback/', views.add_scope_callback, name='add_scope_callback'),
    path('sync_mailing_list', views.SyncMailingListView.as_view(), name='sync_mailing_list'),

    path('my_account', views.MyAccountView.as_view(), name='my_account'),
    path('my_account/remove/<str:provider>', views.remove_social_account, name='remove_social_account'),
    path('details/<username>/<int:days>', views.StudentDetailsView.as_view(), name='student_details'),
]
