import json
import logging
import math
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
from allauth.account.models import EmailAddress
from allauth.socialaccount import signals
from allauth.socialaccount.models import SocialToken, SocialApp, SocialAccount
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from axes import helpers as axes_helpers
from axes.handlers.proxy import AxesProxyHandler
from axes.utils import reset as axes_reset
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, get_user_model, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetCompleteView
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.db.models.functions import Lower
from django.dispatch import receiver
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views import View
from django.views.generic import TemplateView, UpdateView, CreateView, FormView, RedirectView
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from eventlog.models import Event
from eventlog.signals import preference_changed
from eventlog.views import EventMixin
from messagequeue.models import Message, client_side_prefs_change
from oauth2.bookshare.views import is_bookshare_connected, get_organization_name, \
    GENERIC_BOOKSHARE_ACCOUNT_NAMES
from pages.views import ThemedPageMixin, SettingsPageMixin, PeriodChoiceMixin
from roster.forms import SimpleUserCreateForm, UserEditForm, UserRegistrationForm, \
    AccountRoleForm, AgeCheckForm, ClusiveLoginForm, GoogleCoursesForm, PeriodCreateForm, PeriodNameForm
from roster.models import ClusiveUser, Period, PreferenceSet, Roles, ResearchPermissions, MailingListMember, \
    RosterDataSource
from roster.signals import user_registered

logger = logging.getLogger(__name__)

def guest_login(request):
    clusive_user = ClusiveUser.make_guest()
    login(request, clusive_user.user, 'django.contrib.auth.backends.ModelBackend')
    return redirect('dashboard')


class LoginView(auth_views.LoginView):
    template_name='roster/login.html'
    form_class = ClusiveLoginForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lock_out_status'] = self.get_lock_out_status(self.request)
        form = context.get('form')
        if form.errors:
            for err in form.errors.as_data().get('__all__'):
                if err.code == 'email_validate':
                    context['email_validate'] = True
                    username = form.cleaned_data['username']
                    try:
                        user = User.objects.get_by_natural_key(username=username)
                        context['user_id'] = user.id
                    except User.DoesNotExist:
                        logger.error('Email not validated error signalled when account does not exist')
        return context

    def get_lock_out_status(self, request):
        # Default values
        lock_out_status = {
            'user_locked_out': False,
            'num_remaining_attempts': 999,
            'warning_threshold_reached':  False,
            'cool_off_time':  None,
        }
        # Check that the workflow is for a user login.  If so, get the lockout
        # status information.
        username = request.POST.get('username', None)
        if username:
            axes_credentials = axes_helpers.cleanse_parameters({
                settings.AXES_USERNAME_FORM_FIELD: username,
                settings.AXES_PASSWORD_FORM_FIELD: request.POST.get('password'),
            })
            lock_out_status.update(self.get_attempts_status(request, axes_credentials))
            lock_out_status.update(self.get_cool_off_status(request, username))

        return lock_out_status

    def get_attempts_status(self, request, axes_credentials):
        # Determine the number of allowed attempts remaining for the user, and
        # the number of times they have failed thus far.
        failure_limit = axes_helpers.get_failure_limit(request, axes_credentials)
        failures_so_far = AxesProxyHandler.get_failures(request, axes_credentials)
        num_remaining_attempts = failure_limit - failures_so_far
        warning_threshold_reached = (
            num_remaining_attempts > 0 and
            num_remaining_attempts < settings.CLUSIVE_LOGIN_FAILURES_WARNING_THRESHOLD
        )
        return {
            'num_remaining_attempts': num_remaining_attempts,
            'warning_threshold_reached': warning_threshold_reached,
        }

    def get_cool_off_status(self, request, username):
        cool_off_time = None
        user_locked_out = getattr(request, 'axes_locked_out', False)
        if user_locked_out:
            session_lock_out_expires_at = request.session.get('lock_out_expires_at', False)
            if session_lock_out_expires_at:
                # If lock out happened for a previous login attempt, use the
                # session's lock_out_expires_at to calculate how much longer
                # lockout is in effect.
                lock_out_expires_at = datetime.strptime(
                    session_lock_out_expires_at,
                    '%Y-%m-%d %H:%M:%S.%f%z'
                )
                now = timezone.now()
                if lock_out_expires_at < now:
                    # Lock out should have expired by now, but
                    # request.axes_locked_out is still True.  Assume lockout
                    # will be cleared in less than a minute.  Set cool_off_time
                    # to a timedelta of zero.
                    cool_off_time = timedelta()
                else:
                    cool_off_time = lock_out_expires_at - now
            else:
                # User was just locked out.  Calculate and store the
                # lock_out_expires_at in the session.
                cool_off_duration = axes_helpers.get_cool_off()
                lock_out_expires_at = str(timezone.now() + cool_off_duration)
                request.session['lock_out_expires_at'] = lock_out_expires_at
                cool_off_time = cool_off_duration
        else:
            # request.axes_locked_out is not True.  Make sure there is no
            # lingering lock_out_expires_at property in the session.
            try:
                request.session.pop('lock_out_expires_at')
            except:
                pass

        # Make cool_off_time readable
        if cool_off_time is not None :
            cool_off_time = readable_wait_time(cool_off_time)

        return {
            'user_locked_out': user_locked_out,
            'cool_off_time': cool_off_time,
        }


def readable_wait_time(duration: timedelta):
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours}:{minutes:02}'

class PasswordResetResetLockoutView(PasswordResetCompleteView):

    def dispatch(self, *args, **kwargs):
        axes_reset(username=self.request.user.username)
        return super().dispatch(*args, **kwargs)


class SignUpView(EventMixin, ThemedPageMixin, CreateView):
    template_name='roster/sign_up.html'
    model = User
    form_class = UserRegistrationForm

    def get_initial(self, *args, **kwargs):
        initial = super(SignUpView, self).get_initial(**kwargs)
        # If registration during SSO, use info from the SSO user
        if self.request.session.get('sso', False):
            initial['user'] = self.request.user
        return initial

    def dispatch(self, request, *args, **kwargs):
        self.role = kwargs['role']
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.current_clusive_user = request.clusive_user
        self.current_site = get_current_site(request)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['role'] = self.role
        context['isSSO'] = self.request.session.get('sso', False)
        return context

    def form_valid(self, form):
        # Don't call super since that would save the target model, which we might not want.
        target : User
        target = form.instance
        if not self.role in ['TE', 'PA', 'ST']:
            raise PermissionError('Invalid role')
        user: User
        if self.current_clusive_user:
            # There is a logged-in user, either a Guest or an SSO user.
            # Update the ClusiveUser and User objects based on the form target.
            clusive_user: ClusiveUser
            clusive_user = self.current_clusive_user
            isSSO = self.request.session.get('sso', False)
            update_clusive_user(clusive_user,
                                self.role,
                                ResearchPermissions.SELF_CREATED,
                                isSSO,
                                form.cleaned_data['education_levels'])
            user = clusive_user.user
            user.first_name = target.first_name
            # If the user is already logged in via SSO, these fields are already
            # set by the SSO process.  If not an SSO user, get the values from
            # the form.
            if not isSSO:
                user.username = target.username
                user.set_password(form.cleaned_data["password1"])
                user.email = target.email
            user.save()

            # Either log in the SSO user and redirect to the dashboard, or, for
            # Guests signing up, send the confirmation email to the new user and
            # log them in.
            if isSSO:
                login(self.request, user, 'allauth.account.auth_backends.AuthenticationBackend')
                logger.debug('sending signal for new google user who has completed registration')
                user_registered.send(self.__class__, clusive_user=clusive_user)
                return HttpResponseRedirect(reverse('dashboard'))
            else:
                send_validation_email(self.current_site, clusive_user)
                login(self.request, user, 'django.contrib.auth.backends.ModelBackend')
        else:
            # This is a new user.  Save the form target User object, and create a ClusiveUser.
            user = target
            user.set_password(form.cleaned_data["password1"])
            user.save()
            clusive_user = ClusiveUser.objects.create(user=user,
                                                      role=self.role,
                                                      permission=ResearchPermissions.SELF_CREATED,
                                                      anon_id=ClusiveUser.next_anon_id(),
                                                      education_levels = form.cleaned_data['education_levels'],
                                                      )
            send_validation_email(self.current_site, clusive_user)
        return HttpResponseRedirect(reverse('validate_sent', kwargs={'user_id' : user.id}))

    def configure_event(self, event: Event):
        event.page = 'Register'


class ValidateSentView(ThemedPageMixin, TemplateView):
    template_name = 'roster/validate_sent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = User.objects.get(pk=kwargs.get('user_id'))
        context['user_id'] = user.id
        context['email'] = user.email
        context['status'] = 'sent'
        return context


class ValidateResendView(ThemedPageMixin, TemplateView):
    template_name = 'roster/validate_sent.html'

    def get(self, request, *args, **kwargs):
        self.user = User.objects.get(pk=kwargs.get('user_id'))
        clusive_user = ClusiveUser.objects.get(user=self.user)
        if clusive_user.unconfirmed_email:
            send_validation_email(get_current_site(request), clusive_user)
            self.status = 'resent'
        else:
            logger.warning('Skipping email sending; already activated user %s', clusive_user)
            self.status = 'unneeded'
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_id'] = self.user.id
        context['email'] = self.user.email
        context['status'] = self.status
        return context


class ValidateEmailView(View):
    template = 'roster/validate.html'

    def get(self, request, *args, **kwargs):
        uid = kwargs.get('user_id')
        token = kwargs.get('token')
        user_model = get_user_model()
        try:
            user = user_model.objects.get(pk=uid)
            clusive_user = ClusiveUser.objects.get(user=user)
            if clusive_user.unconfirmed_email:
                check_token = default_token_generator.check_token(user, token)
                if check_token:
                    logger.info('Activating user %s', user)
                    clusive_user.unconfirmed_email = False
                    clusive_user.save()
                    result = 'activated'
                    logger.debug('sending signal for new user who has completed email validation')
                    user_registered.send(self.__class__, clusive_user=clusive_user)
                else:
                    logger.warning('Email validation check failed. User=%s; token=%s; result=%s',
                                user, token, check_token)
                    result = 'error'
            else:
                logger.warning('Skipping activation of already activated user %s', user)
                result = 'unneeded'
        except:
            result = 'error'
        context = {
            'status': result,
            'user_id': uid
        }
        return render(request, self.template, context)


class SignUpRoleView(EventMixin, ThemedPageMixin, FormView):
    form_class = AccountRoleForm
    template_name = 'roster/sign_up_role.html'

    def form_valid(self, form):
        clusive_user = self.request.clusive_user
        role = form.cleaned_data['role']
        if role == Roles.STUDENT:
            self.success_url = reverse('sign_up_age_check')
        else:
            # Logging in via SSO for the first time entails that there is a
            # clusive_user and its role is UNKNOWN
            isSSO = True if (clusive_user and clusive_user.role == Roles.UNKNOWN) else False
            if isSSO:
                update_clusive_user(clusive_user,
                                    role,
                                    ResearchPermissions.SELF_CREATED,
                                    isSSO)
            self.success_url = reverse('sign_up', kwargs={'role': role, 'isSSO': isSSO})
        return super().form_valid(form)

    def configure_event(self, event: Event):
        event.page = 'RegisterRole'


class SignUpAgeCheckView(EventMixin, ThemedPageMixin, FormView):
    form_class = AgeCheckForm
    template_name = 'roster/sign_up_age_check.html'

    def form_valid(self, form):
        clusive_user = self.request.clusive_user
        logger.debug("of age: %s", repr(form.cleaned_data['of_age']))
        if form.cleaned_data['of_age'] == 'True':
            # Logging in via SSO for the first time entails that there is a
            # clusive_user and its role is UNKNOWN
            isSSO = True if (clusive_user and clusive_user.role == Roles.UNKNOWN) else False
            if clusive_user and clusive_user.role == Roles.UNKNOWN:
                update_clusive_user(self.request.clusive_user,
                                    Roles.STUDENT,
                                    ResearchPermissions.SELF_CREATED,
                                    isSSO)
            self.success_url = reverse('sign_up', kwargs={'role': Roles.STUDENT, 'isSSO': isSSO})
        else:
            self.success_url = reverse('sign_up_ask_parent')
        return super().form_valid(form)

    def configure_event(self, event: Event):
        event.page = 'RegisterAge'


class SignUpAskParentView(EventMixin, ThemedPageMixin, TemplateView):
    template_name = 'roster/sign_up_ask_parent.html'

    def get(self, request, *args, **kwargs):
        # Create and log the event as usual, but then delete any SSO underage
        # student records.
        result = super().get(request, *args, **kwargs)
        logout_sso(request, 'student')
        return result

    def configure_event(self, event: Event):
        event.page = 'RegisterAskParent'

class PreferenceView(View):

    def get(self, request):
        user = ClusiveUser.from_request(request)
        return JsonResponse(user.get_preferences_dict())

    def post(self, request):
        try:
            request_prefs = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': 0, 'message': 'Invalid JSON in request'})

        user = ClusiveUser.from_request(request)
        set_user_preferences(user, request_prefs, None, None, request)

        return JsonResponse({'success': 1})


# TODO: should we specially log an event that adopts a full new preference set?
class PreferenceSetView(View):

    def post(self, request):
        user = ClusiveUser.from_request(request)
        try:
            request_json = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': 0, 'message': 'Invalid JSON in request'})

        desired_prefs_name = request_json["adopt"]
        event_id = request_json["eventId"]
        timestamp = timezone.now()

        try:
            desired_prefs = PreferenceSet.get_json(desired_prefs_name)
        except PreferenceSet.DoesNotExist:
            return JsonResponse(status=404, data={'message': 'Preference set named %s does not exist' % desired_prefs_name})

        set_user_preferences(user, desired_prefs, event_id, timestamp, request)

        # Return the preferences set
        return JsonResponse(desired_prefs)


# Set user preferences from a dictionary
def set_user_preferences(user, new_prefs, event_id, timestamp, request, reader_info=None):
    """Sets User's preferences to match the given dictionary of preference values."""
    old_prefs = user.get_preferences_dict()
    prefs_to_use = new_prefs
    for pref_key in prefs_to_use:
        old_val = old_prefs.get(pref_key)
        if old_val != prefs_to_use[pref_key]:
            # Preference changes associated with a page event (user action)
            if(event_id):
                set_user_preference_and_log_event(user, pref_key, prefs_to_use[pref_key], event_id, timestamp, request, reader_info=reader_info)
            # Preference changes not associated with a page event - not logged
            else:
                user.set_preference(pref_key, prefs_to_use[pref_key])

            # logger.debug("Pref %s changed %s (%s) -> %s (%s)", pref_key,
            #              old_val, type(old_val),
            #              pref.typed_value, type(pref.typed_value))

def set_user_preference_and_log_event(user, pref_key, pref_value, event_id, timestamp, request, reader_info=None):
    pref = user.set_preference(pref_key, pref_value)
    preference_changed.send(sender=ClusiveUser.__class__, request=request, event_id=event_id, preference=pref, timestamp=timestamp, reader_info=reader_info)

@receiver(client_side_prefs_change, sender=Message)
def set_preferences_from_message(sender, content, timestamp, request, **kwargs):
    logger.debug("client_side_prefs_change message received")
    reader_info = content.get("readerInfo")
    user = request.clusive_user
    set_user_preferences(user, content["preferences"], content["eventId"], timestamp, request, reader_info=reader_info)


class ManageView(LoginRequiredMixin, EventMixin, ThemedPageMixin, SettingsPageMixin, PeriodChoiceMixin, TemplateView):
    template_name = 'roster/manage.html'

    def get(self, request, *args, **kwargs):
        user = request.clusive_user
        if not user.can_manage_periods:
            self.handle_no_permission()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.current_period is not None:
            context['people'] = self.make_people_info_list(self.request.user)
            context['period_name_form'] = PeriodNameForm(instance=self.current_period)
        return context

    def make_people_info_list(self, current_user):
        people = self.current_period.users.exclude(user=current_user).order_by(Lower('user__first_name'))
        return [{
            'info': {
                'first_name': p.user.first_name,
                'email': p.user.email,
                'role' : Roles.display_name(p.role),
                'id': p.user.id
            }
        } for p in people]

    def configure_event(self, event: Event):
        event.page = 'Manage'


class ManageCreateUserView(LoginRequiredMixin, EventMixin, ThemedPageMixin, SettingsPageMixin, CreateView):
    model = User
    form_class = SimpleUserCreateForm
    template_name = 'roster/manage_create_user.html'
    period = None

    def dispatch(self, request, *args, **kwargs):
        self.period = get_object_or_404(Period, id=kwargs['period_id'])
        # Sanity check requested period
        cu = request.clusive_user
        if not cu.can_manage_periods or not self.period.users.filter(id=cu.id).exists():
            self.handle_no_permission()
        self.creating_user_role = cu.role
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('manage', kwargs={'period_id': self.period.id})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['period_id'] = self.period.id
        return data

    def form_valid(self, form):
        # Create User
        form.save()
        target : User
        target = form.instance
        # Set password
        new_pw = form.cleaned_data['password']
        if new_pw:
            target.set_password(new_pw)
            target.save()
        # Create ClusiveUser
        if self.creating_user_role == Roles.TEACHER:
            perm = ResearchPermissions.TEACHER_CREATED
        elif self.creating_user_role == Roles.PARENT:
            perm = ResearchPermissions.PARENT_CREATED
        else:
            self.handle_no_permission()
        cu = ClusiveUser.objects.create(user=target,
                                        role=Roles.STUDENT,
                                        anon_id=ClusiveUser.next_anon_id(),
                                        permission=perm)

        # Add user to the Period
        self.period.users.add(cu)
        return super().form_valid(form)

    def configure_event(self, event: Event):
        event.page = 'ManageCreateStudent'

class ManageEditUserView(LoginRequiredMixin, EventMixin, ThemedPageMixin, SettingsPageMixin, UpdateView):
    model = User
    form_class = UserEditForm
    template_name = 'roster/manage_edit_user.html'
    period = None

    def dispatch(self, request, *args, **kwargs):
        self.period = get_object_or_404(Period, id=kwargs['period_id'])
        # Sanity check requested period
        cu = request.clusive_user
        if not cu.can_manage_periods or not self.period.users.filter(id=cu.id).exists():
            self.handle_no_permission()
        # Sanity check requested User. Associated ClusiveUser should be a member of that Period.
        target = get_object_or_404(User, id=kwargs['pk'])
        if not self.period.users.filter(user__id=target.id).exists():
            self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('manage', kwargs={'period_id': self.period.id})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['period_id'] = self.period.id
        return data

    def form_valid(self, form):
        form.save()
        target : User
        target = form.instance
        new_pw = form.cleaned_data.get('password')
        if new_pw:
            target.set_password(new_pw)
            target.save()
        return super().form_valid(form)

    def configure_event(self, event: Event):
        event.page = 'ManageEditStudent'


class ManageEditPeriodView(LoginRequiredMixin, EventMixin, ThemedPageMixin, SettingsPageMixin, UpdateView):
    model = Period
    form_class = PeriodNameForm
    template_name = 'roster/manage_edit_period.html'

    def dispatch(self, request, *args, **kwargs):
        cu = request.clusive_user
        if not cu.can_manage_periods or not self.get_object().users.filter(id=cu.id).exists():
            self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('manage', kwargs={'period_id': self.object.id})

    def configure_event(self, event: Event):
        event.page = 'ManageEditPeriod'


class ManageCreatePeriodView(LoginRequiredMixin, EventMixin, ThemedPageMixin, SettingsPageMixin, CreateView):
    """
    Displays a choice for the user between the various supported methods for creating a new Period.
    Options are manual (always available) and importing from Google Classroom (if user has a connected Google acct).
    Redirects to manage page for manual creation, or to GetGoogleCourses.
    """
    model = Period
    form_class = PeriodCreateForm
    template_name = 'roster/manage_create_period.html'

    def get_form(self, form_class=None):
        instance=Period(site=self.clusive_user.get_site())
        kwargs = self.get_form_kwargs()
        kwargs['instance'] = instance
        kwargs['allow_google'] = (self.clusive_user.data_source == RosterDataSource.GOOGLE)
        logger.debug('kwargs %s', kwargs)
        return PeriodCreateForm(**kwargs)

    def dispatch(self, request, *args, **kwargs):
        cu = request.clusive_user
        if not cu.can_manage_periods:
            self.handle_no_permission()
        self.clusive_user = cu
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('manage', kwargs={'period_id': self.object.id})

    def form_valid(self, form):
        if form.cleaned_data.get('create_or_import') == 'google':
            # Do not save the period, just redirect.
            return HttpResponseRedirect(reverse('get_google_courses'))
        else:
            # Save Period and add current user
            result = super().form_valid(form)
            self.object.users.add(self.clusive_user)
            return result

    def configure_event(self, event: Event):
        event.page = 'ManageCreatePeriod'

def finish_login(request):
    """
    Called as the redirect after Google Oauth SSO login.
    Checks if we need to ask user for their role and privacy policy agreement, or if that's already done.
    """
    if request.user.is_staff:
        return HttpResponseRedirect('/admin')
    clusive_user = ClusiveUser.from_request(request)
    google_user = SocialAccount.objects.filter(user=request.user, provider='google')
    if google_user:
        # If you're logging in via Google, then you are marked as a Google user from now on.
        if clusive_user.data_source != RosterDataSource.GOOGLE:
            logger.debug("  Changing user to Google user")
            clusive_user.data_source = RosterDataSource.GOOGLE
            clusive_user.external_id = google_user[0].uid
            clusive_user.save()
    else:
        # Not a Google user
        if clusive_user.data_source != RosterDataSource.CLUSIVE:
            logger.debug("  Changing user to non-google user")
            clusive_user.data_source = RosterDataSource.CLUSIVE
            clusive_user.save()

    # Check for valid Bookshare access token for this user.
    if is_bookshare_connected(request):
        request.session['bookshare_connected'] = True
    else:
        request.session['bookshare_connected'] = False

    # If you haven't logged in before, your role will be UNKNOWN and we need to ask you for it.
    if clusive_user.role == Roles.UNKNOWN:
        request.session['sso'] = True
        return HttpResponseRedirect(reverse('sign_up_role'))
    else:
        return HttpResponseRedirect(reverse('dashboard'))


def update_clusive_user(current_clusive_user, role, permissions, isSSO, edu_levels=None):
    clusive_user: ClusiveUser
    clusive_user = current_clusive_user
    logger.debug('Updating %s from %s to %s', clusive_user, clusive_user.role, role)
    clusive_user.role = role
    clusive_user.permission = permissions
    if isSSO:
        clusive_user.unconfirmed_email = False
    if edu_levels:
        clusive_user.education_levels = edu_levels
    clusive_user.save()


def send_validation_email(site, clusive_user : ClusiveUser):
    clusive_user.unconfirmed_email = True
    clusive_user.save()
    user = clusive_user.user
    token = default_token_generator.make_token(user)
    logger.info('Generated validation token for user: %s %s', user, token)
    context = {
        'site_name': site.name,
        'domain': site.domain,
        'protocol': 'https', # Note, this will send incorrect URLs in local development without https.
        'email': user.email,
        'uid': user.pk,
        'user': user,
        'token': token,
    }
    subject = loader.render_to_string('roster/validate_subject.txt', context)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    body = loader.render_to_string('roster/validate_email.txt', context)
    from_email = None  # Uses default specified in settings
    email_message = EmailMultiAlternatives(subject, body, from_email, [user.email])
    # TODO add if we create HTML email
    # if html_email_template_name is not None:
    #     html_email = loader.render_to_string(html_email_template_name, context)
    #     email_message.attach_alternative(html_email, 'text/html')
    email_message.send()

def cancel_registration(request):
    logger.debug("Cancelling registration")
    logout_sso(request)
    return HttpResponseRedirect('/')

def logout_sso(request, student=''):
    """This is used in the cases where (1) an SSO user has cancelled the
    registration process or (2) a student signed up using SSO, but is not of
    age.  Remove associated User, ClusiveUser, SocialAccount, and AccessToken
    records, effectively logging out.  If not an SSO situation, this does
    nothing."""
    clusive_user = request.clusive_user
    if (clusive_user and clusive_user.role == Roles.UNKNOWN) or request.session.get('sso', False):
        logger.debug("SSO logout, and removing records for %s %s", student, clusive_user)
        django_user = request.user
        logout(request)
        django_user.delete()
    else:
        logger.debug("Unregistered user, nothing to delete")


class SyncMailingListView(View):
    """
    Called by script to periodically send new member info to the mailing list software.
    """

    def get(self, request):
        logger.debug('Sync mailing list request received')
        messages = MailingListMember.synchronize_user_emails()
        return JsonResponse({
            'success': 1,
            'messages': messages,
        })


class GoogleCoursesView(LoginRequiredMixin, EventMixin, ThemedPageMixin, TemplateView, FormView):
    """
    Displays the list of Google Classroom courses and allows user to choose one to import.
    Expects to receive a 'google_courses' parameter in the session, which is a list of dicts
    each of which has at least 'name', 'id', and 'imported' (aka already exists in Clusive).
    See GetGoogleCourses, which sets this.
    After choice is made, redirects to GetGoogleRoster.
    """
    form_class = GoogleCoursesForm
    courses = []
    template_name = 'roster/manage_show_google_courses.html'

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        return GoogleCoursesForm(**kwargs, courses = self.request.session.get('google_courses', []))

    def dispatch(self, request, *args, **kwargs):
        cu = request.clusive_user
        if not cu.can_manage_periods:
            self.handle_no_permission()
        self.clusive_user = cu
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        selected_course_id = self.request.POST.get('course_select')
        return reverse('get_google_roster', kwargs={'course_id': selected_course_id})

    def configure_event(self, event: Event):
        event.page = 'ManageImportPeriodChoice'

class GoogleRoleMap:
    ROLE_MAP = { 'students': Roles.STUDENT, 'teachers': Roles.TEACHER }

    @classmethod
    def clusive_display_name(cls, google_role):
        return Roles.display_name(GoogleRoleMap.ROLE_MAP[google_role])

class GoogleRosterView(LoginRequiredMixin, ThemedPageMixin, EventMixin, TemplateView):
    """
    Display the roster of a google class, allow user to confirm whether it should be imported.
    Expects google_courses and google_roster parameters in the session: see GetGoogleRoster method.
    The roster is saved in the session for use if the user confirms creation.
    """
    template_name = 'roster/manage_show_google_roster.html'

    def make_roster_tuples(self, google_roster):
        tuples = []
        for group in google_roster:
            for person in google_roster[group]:
                email = person['profile']['emailAddress']
                google_id = person['profile']['id']
                users = User.objects.filter(email=email)
                if users.exists():
                    user_with_that_email = users.first()
                    # Exclude the current user from the roster.
                    if self.request.user == user_with_that_email:
                        continue
                    clusive_user = ClusiveUser.objects.get(user=user_with_that_email)
                    a_person = {
                        'name': user_with_that_email.first_name,
                        'email': email,
                        'role': clusive_user.role,
                        'role_display': Roles.display_name(clusive_user.role),
                        'exists': True,
                        'external_id': google_id
                    }
                else:
                    a_person = {
                        'name': person['profile']['name']['givenName'],
                        'email': email,
                        'role': GoogleRoleMap.ROLE_MAP[group],
                        'role_display': GoogleRoleMap.clusive_display_name(group),
                        'exists': False,
                        'external_id': google_id
                    }
                tuples.append(a_person)
        return tuples

    def dispatch(self, request, *args, **kwargs):
        cu = request.clusive_user
        if not cu.can_manage_periods:
            self.handle_no_permission()
        self.clusive_user = cu

        # API returns all courses, we need to search for the one we're importing.
        google_courses = self.request.session.get('google_courses', [])
        self.course = None
        for course in google_courses:
            if course['id'] == kwargs['course_id']:
                self.course = course
                break
        if not self.course:
            raise PermissionDenied('Course not found')

        # Period name for Clusive is a composite of Google's "name" and (optional) "section"
        self.period_name = self.course['name']
        if 'section' in self.course:
            self.period_name += ' ' + self.course['section']

        # Extract interesting data from the Google roster.
        google_roster = self.request.session.get('google_roster', {})
        self.people = self.make_roster_tuples(google_roster)
        # Data stored in session until user confirms addition (or cancels).
        # Consider also keeping:  course descriptionHeading, updateTime, courseState
        course_data = {
            'id': self.course['id'],
            'name': self.period_name,
            'people': self.people,
        }
        request.session['google_period_import'] = course_data
        logger.debug('Session data stored: %s', course_data)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'course_id': self.course['id'],
            'period_name': self.period_name,
            'people': self.people,
        })
        return context

    def configure_event(self, event: Event):
        event.page = 'ManageImportPeriodConfirm'

class GooglePeriodImport(LoginRequiredMixin, RedirectView):
    """
    Import new Period data that was just confirmed, then redirect to manage page.
    """

    def get(self, request, *args, **kwargs):
        course_id = kwargs['course_id']
        session_data = request.session.get('google_period_import', None)
        if not session_data or session_data['id'] != course_id:
            raise PermissionDenied('Import data is out of date')
        creator = request.clusive_user

        # Find or create user accounts
        user_list = [creator]
        creating_permission = ResearchPermissions.TEACHER_CREATED if creator.role == Roles.TEACHER \
            else ResearchPermissions.PARENT_CREATED
        for person in session_data['people']:
            if person['exists']:
                clusive_user = ClusiveUser.objects.get(user__email=person['email'])
                clusive_user.external_id = person['external_id']
                clusive_user.save()
                user_list.append(clusive_user)
            else:
                properties = {
                    'username': person['email'],
                    'email': person['email'],
                    'first_name': person['name'],
                    'role': person['role'],
                    'permission': creating_permission,
                    'anon_id': ClusiveUser.next_anon_id(),
                    'data_source': RosterDataSource.GOOGLE,
                    'external_id': person['external_id'],
                }
                user_list.append(ClusiveUser.create_from_properties(properties))

        # Create Period
        period = Period.objects.create(name=session_data['name'],
                                       site=creator.get_site(),
                                       data_source=RosterDataSource.GOOGLE,
                                       external_id=session_data['id'])
        period.users.set(user_list)
        period.save()
        self.period = period

        return super().get(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        # Redirect to newly created period
        return reverse('manage', kwargs={'period_id': self.period.id})

class GetGoogleCourses(LoginRequiredMixin, View):
    """
    Calls the Google Classroom API to get a list of courses for this user, then redirects to GoogleCoursesView.
    Requests additional Google permissions if necessary.
    """
    provider = 'google'
    classroom_scopes = 'https://www.googleapis.com/auth/classroom.courses.readonly https://www.googleapis.com/auth/classroom.rosters.readonly https://www.googleapis.com/auth/classroom.profile.emails'
    auth_parameters = urlencode({
        'provider': provider,
        'scopes': classroom_scopes,
        'authorization': 'http://accounts.google.com/o/oauth2/v2/auth?'
    })

    def get(self, request, *args, **kwargs):
        logger.debug("GetGoogleCourses")
        teacher_id = self.google_teacher_id(request.user)
        if teacher_id:
            db_access = OAuth2Database()
            user_credentials = self.make_credentials(request.user, self.classroom_scopes, db_access)
            service = build('classroom', 'v1', credentials=user_credentials)
            try:
                results = service.courses().list(teacherId=teacher_id, pageSize=30).execute()
            except HttpError as e:
                if e.status_code == 403:
                    request.session['add_scopes_return_uri'] = 'get_google_courses'
                    request.session['add_scopes_course_id'] = None
                    return HttpResponseRedirect(reverse('add_scope_access') + '?' + self.auth_parameters)
                else:
                    raise
            courses = results.get('courses', [])
        else:
            courses = []
        logger.debug('There are (%s) Google courses', len(courses))
        for course in courses:
            course['imported'] = Period.objects.filter(data_source=RosterDataSource.GOOGLE, external_id=course['id']).exists()
            logger.debug('- %s, id = %s. Imported=%s', course['name'], course['id'], course['imported'])
        request.session['google_courses'] = courses
        return HttpResponseRedirect(reverse('manage_google_courses'))

    def make_credentials(self, user, scopes, db_access):
        client_info = db_access.retrieve_client_info(self.provider)
        access_token = db_access.retrieve_access_token(user, self.provider)
        return Credentials(access_token.token,
                            refresh_token=access_token.token_secret,
                            client_id=client_info.client_id,
                            client_secret=client_info.secret,
                            token_uri='https://accounts.google.com/o/oauth2/token')

    def google_teacher_id(self, user):
        # Rationale: Google teacher identifer can be the special key 'me', the
        # user's Google account email address, or their Google identifier.  Only
        # the latter is guaranteed to match a Google course's teacher
        # identifier.
        # https://developers.google.com/classroom/reference/rest/v1/courses/list
        try:
            google_user = SocialAccount.objects.get(user=user, provider='google')
            return google_user.uid
        except SocialAccount.DoesNotExist:
            logger.debug('User %s is not an SSO user', user.username)
            return None

class GetGoogleRoster(GetGoogleCourses):
    """
    Calls Google Classroom API to get the roster of a given course, then redirects to GoogleRosterView.
    """

    def get(self, request, *args, **kwargs):
        # There should always be a `course_id` which identifies a Google course,
        # but the context may or may not include a Clusive `period_id`
        course_id = kwargs.get('course_id')
        period_id = kwargs.get('period_id')
        db_access = OAuth2Database()
        user_credentials = self.make_credentials(request.user, self.classroom_scopes, db_access)
        service = build('classroom', 'v1', credentials=user_credentials)

        # TODO:  could get a permission error, not because of lack of scope, but
        # because the access_token has expired, and need a new one.  Should use
        # the `refresh` workflow instead of the `code` workflow -- the latter
        # will always work, however.  Question is, can you tell from the
        # authorization error (HttpError) if it's lack of scope or expired
        # token?
        # Note: documentation for `pageSize` query parameter (defaults to 30):
        # https://developers.google.com/classroom/reference/rest/v1/courses.students/list
        # https://developers.google.com/classroom/reference/rest/v1/courses.teachers/list
        try:
            studentResponse = service.courses().students().list(courseId=course_id, pageSize=100).execute()
            teacherResponse = service.courses().teachers().list(courseId=course_id).execute()
        except HttpError as e:
            if e.status_code == 403:
                request.session['add_scopes_return_uri'] = 'get_google_roster'
                request.session['add_scopes_course_id'] = course_id
                request.session['add_scopes_period_id'] = period_id
                return HttpResponseRedirect(reverse('add_scope_access') + '?' + self.auth_parameters)
            else:
                raise
        students = studentResponse.get('students', [])
        teachers = teacherResponse.get('teachers', [])
        self.log_results(students, 'students')
        self.log_results(teachers, 'teachers')

        request.session['google_roster'] = { 'students': students, 'teachers': teachers }
        if period_id is not None:
            return HttpResponseRedirect(reverse('google_roster_sync', kwargs=kwargs))
        else:
            return HttpResponseRedirect(reverse('manage_google_roster', kwargs={'course_id': course_id}))

    def log_results(self, group, role):
        logger.debug('Get Google roster: there are (%s) %s', len(group), role)
        for person in group:
            logger.debug('- %s, %s', person['profile']['name']['givenName'], person['profile']['emailAddress'])

class GoogleRosterSyncView(LoginRequiredMixin, ThemedPageMixin, TemplateView):
    """
    Calls GetGoogleRoster to get the current google classroom roster associated
    with the Period and displays what needs updating.
    """
    period = None
    google_roster = {}
    period_roster = None
    roster_updates = []
    any_changes = False
    template_name = 'roster/manage_review_google_sync_roster.html'

    def dispatch(self, request, *args, **kwargs):
        cu = request.clusive_user
        self.period = get_object_or_404(Period, pk=kwargs.get('period_id'))

        if not cu.can_manage_periods:
            self.handle_no_permission()

        # Extract a list of people from the Google roster and the Period's
        # roster to make the list of updates.
        self.google_roster = self.request.session.get('google_roster', {})
        self.period_roster = self.period.users.exclude(user=request.user).order_by('user__first_name')
        self.roster_updates = self.make_roster_updates(cu)
        request.session['google_roster_updates'] = {
            'period_id': self.period.id,
            'roster_updates': self.roster_updates
        }
        logger.debug('Session data (roster updates) stored: %s', self.roster_updates)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_period'] = self.period
        if self.period is not None:
            context['roster_updates'] = self.roster_updates
            context['any_changes'] = self.any_changes
            context['course_id'] = kwargs['course_id']
            context['current_period'] = self.period
        return context

    def make_roster_updates(self, teacher):
        updates = []
        # 1. Loop to find clusive_users in the Period that are either (1) in the
        # google_roster whose email may have changed or (2) no longer in the
        # google_roster
        for clusive_user in self.period_roster:
            google_user = None
            google_id = clusive_user.external_id
            clusive_email = clusive_user.user.email
            for group in self.google_roster:
                if google_id:
                    google_user = next((person for person in self.google_roster[group] if person['profile']['id'] == google_id), None)
                else:
                    # In case an external_id was not stored in the clusive_user
                    # when it was created, then use its email.  Also, take the
                    # time to record the external_id now.
                    google_user = next((person for person in self.google_roster[group] if person['profile']['emailAddress'] == clusive_email), None)
                    if google_user:
                        google_id = google_user['profile']['id']
                        clusive_user.external_id = google_id
                        clusive_user.save()

                if google_user:     # google_user is a clusive_user
                    break

            if google_user is not None:
                # Found clusive_user in the Period that is also in the
                # google_roster.
                an_update = {}
                an_update['exists'] = True
                an_update['in_period'] = True
                an_update['name'] = clusive_user.user.first_name
                an_update['role'] = clusive_user.role
                an_update['role_display'] = Roles.display_name(clusive_user.role)
                self.check_email(clusive_user, google_user, an_update)
                an_update['google_id'] = google_id
                updates.append(an_update)

            else:
                # clusive_user in Period but not in google_roster implies the
                # google person left the google classroom.  The update is that
                # the corrsponding clusive_user is to be removed from the
                # Period.
                an_update = {}
                an_update['exists'] = True
                an_update['in_period'] = True
                an_update['remove'] = True
                an_update['name'] = clusive_user.user.first_name
                an_update['email'] = clusive_user.user.email
                an_update['role'] = clusive_user.role
                an_update['role_display'] = Roles.display_name(clusive_user.role)
                an_update['google_id'] = clusive_user.external_id
                self.any_changes = True
                updates.append(an_update)

        # 2. Loop through the google_roster to find people in the google class
        # who need to be added to the Period
        for group in self.google_roster:
            for google_user in self.google_roster[group]:
                google_id = google_user['profile']['id']
                google_email = google_user['profile']['emailAddress']
                clusive_user = None
                if ClusiveUser.objects.filter(external_id=google_id).exists():
                    clusive_user = ClusiveUser.objects.get(external_id=google_id)
                elif User.objects.filter(email=google_email).exists():
                    # In case an external_id was not stored in the clusive_user
                    # when it was created, then use its email.  Also, record
                    # the external_id for future use.
                    user_via_email = User.objects.get(email=google_email)
                    clusive_user = ClusiveUser.objects.get(user=user_via_email)
                    clusive_user.external_id = google_id
                    clusive_user.save()

                if clusive_user:
                    if clusive_user == teacher:
                        continue
                    try:
                        self.period_roster.get(id=clusive_user.id)
                        # Google person has a Clusive account and is in the
                        # period.  Already dealt with in Loop #1
                        continue
                    except:
                        # Google person in google class has a Clusive account,
                        # but is not in Period, add them.
                        an_update = {}
                        an_update['exists'] = True
                        an_update['in_period'] = False
                        an_update['name'] = clusive_user.user.first_name
                        an_update['role'] = clusive_user.role
                        an_update['role_display'] = Roles.display_name(clusive_user.role)
                        self.check_email(clusive_user, google_user, an_update)
                        an_update['google_id'] = google_id
                        self.any_changes = True
                        updates.append(an_update)
                else:
                    # Google person in google class but does not even have a
                    # Clusive account.
                    an_update = {}
                    an_update['exists'] = False
                    an_update['in_period'] = False
                    an_update['name'] = google_user['profile']['name']['givenName']
                    an_update['email'] = google_user['profile']['emailAddress']
                    an_update['role'] = GoogleRoleMap.ROLE_MAP[group]
                    an_update['role_display'] = GoogleRoleMap.clusive_display_name(group)
                    an_update['google_id'] = google_id
                    self.any_changes = True
                    updates.append(an_update)
            # end google_user loop
        # end google group loop
        return updates

    def check_email(self, clusive_user, google_user, an_update):
        if clusive_user.user.email != google_user['profile']['emailAddress']:
            an_update['new_email'] = True
            an_update['email'] = google_user['profile']['emailAddress']
            self.any_changes = True
        else:
            an_update['new_email'] = False
            an_update['email'] = clusive_user.user.email

class GooglePeriodRosterUpdate(LoginRequiredMixin, RedirectView):
    """
    Import updates to the Period roster that was just confirmed, then redirect
    to manage page.
    """
    period = None

    def get(self, request, *args, **kwargs):
        period_id = kwargs['period_id']
        period = get_object_or_404(Period, pk=period_id)

        session_data = request.session.get('google_roster_updates', None)
        if not session_data or session_data['period_id'] != period_id:
            raise PermissionDenied('Roster updates are out of date')
        creator = request.clusive_user
        period_roster = period.users.exclude(user=request.user).order_by('user__first_name')
        logger.debug('period_roster: %s', period_roster)

        # Find or create user accounts, "remove" users from Period
        creating_permission = ResearchPermissions.TEACHER_CREATED if creator.role == Roles.TEACHER \
            else ResearchPermissions.PARENT_CREATED
        for person in session_data['roster_updates']:
            if not person.get('exists', False):
                properties = {
                    'username': person['email'],
                    'email': person['email'],
                    'first_name': person['name'],
                    'role': person['role'],
                    'permission': creating_permission,
                    'anon_id': ClusiveUser.next_anon_id(),
                    'data_source': RosterDataSource.GOOGLE,
                    'external_id': person['google_id'],
                }
                clusive_user = ClusiveUser.create_from_properties(properties)
                period.users.add(clusive_user)
                clusive_user.save()

            elif person.get('in_period', False) == False:
                clusive_user = ClusiveUser.objects.get(external_id=person['google_id'])
                period.users.add(clusive_user)
                clusive_user.save()

            elif person.get('remove', False):
                user_to_remove = ClusiveUser.objects.get(external_id=person['google_id'])
                period.users.remove(user_to_remove)
                user_to_remove.save()

            elif person.get('new_email', False):
                # (Google) SSO users have an associated EmailAddress -- update
                # both their User.email and their EmailAddress, if any.  There
                # is no EmailAddress if `person` has yet to register with
                # Clusive.
                clusive_user = ClusiveUser.objects.get(external_id=person['google_id'])
                clusive_user.user.email = person['email']
                clusive_user.user.save()
                try:
                    email_address = EmailAddress.objects.get(user_id=clusive_user.user.id)
                    email_address.email = person['email']
                    email_address.save()
                except EmailAddress.DoesNotExist:
                    pass
            else:
                # Person already in period, with no changes -- nothing to add(),
                # remove(), nor update.
                logger.debug("User %s already in period %s", person['email'], period.name)

        period.save()
        self.period = period
        return super().get(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        # Redirect to newly updated period
        return reverse('manage', kwargs={'period_id': self.period.id})

########################################
#
# Functions for adding scope(s) workflow

class OAuth2Database(object):

    def retrieve_client_info(self, provider):
        client_info = SocialApp.objects.filter(provider=provider).first()
        return client_info

    def retrieve_access_token(self, user, provider):
        access_token = SocialToken.objects.filter(
            account__user=user, account__provider=provider
        ).first()
        return access_token

    def update_access_token(self, access_token_json, user, provider):
        db_token = self.retrieve_access_token(user, provider)
        db_token.token = access_token_json.get('access_token')
        db_token.expires_at = timezone.now() + timedelta(seconds=int(access_token_json.get('expires_in')))

        # Update the refresh token only if a new one was provided.  OAuth2
        # providers don't always send a refresh token.
        if access_token_json.get('refresh_token') != None:
            db_token.token_secret = access_token_json['refresh_token']
        db_token.save()

def add_scope_access(request):
    """First step for the request-additional-scope-access workflow.  Sets a new
    `state` query parameter (the anti-forgery token) for the workflow, and
    stores it in the session as `oauth2_state`.  Redirects to provider's
    authorization end point."""
    provider = request.GET.get('provider')
    new_scopes = request.GET.get('scopes')
    authorization_uri = request.GET.get('authorization')
    oauth2_state = get_random_string(12)
    request.session['oauth2_state'] = oauth2_state

    client_info = OAuth2Database().retrieve_client_info(provider)
    parameters = urlencode({
        'client_id': client_info.client_id,
        'response_type': 'code',
        'scope': new_scopes,
        'include_granted_scopes': 'true',
        'state': oauth2_state,
        'redirect_uri': get_add_scope_redirect_uri(request),
    })
    logger.debug('Authorization request to provider for larger scope access')
    return HttpResponseRedirect(authorization_uri + parameters)

def add_scope_callback(request):
    """Handles callback from OAuth2 provider where access tokens are given for
    the requested scopes."""
    request_state = request.GET.get('state')
    session_state = request.session.get('oauth2_state')
    if request_state != session_state:
        raise OAuth2Error("Mismatched state in request: %s" % request_state)

    code = request.GET.get('code')
    dbAccess = OAuth2Database()
    # TODO: the provider is hard coded here -- how to parameterize?  Note that
    # this function is specific to google, so perhaps okay.
    client_info = dbAccess.retrieve_client_info('google')
    logger.debug('Token request to provider for larger scope access')
    resp = requests.request(
        'POST',
        'https://accounts.google.com/o/oauth2/token',
        data={
            'redirect_uri': get_add_scope_redirect_uri(request),
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': client_info.client_id,
            'client_secret': client_info.secret,
            'state': request_state
        }
    )
    access_token = None
    if resp.status_code == 200 or resp.status_code == 201:
        access_token = resp.json()
    if not access_token or access_token.get('access_token') == None:
        raise OAuth2Error("Error retrieving access token: none given, status: %d" % resp.status_code)
    dbAccess.update_access_token(access_token, request.user, 'google')

    # TODO:  There has to be a better way.
    return_uri = request.session['add_scopes_return_uri']
    course_id = request.session.get('add_scopes_course_id')
    period_id = request.session.get('add_scopes_period_id')
    logger.debug('Larger scope access request complete, returning to %s, with course id %s', return_uri, course_id)
    if course_id:
        return HttpResponseRedirect(reverse(return_uri, kwargs={'course_id': course_id, 'period_id': period_id}))
    else:
        return HttpResponseRedirect(reverse(return_uri))


def get_add_scope_redirect_uri(request):
    # Determine if we are using HTTPS - outside any reverse proxy.
    # Would be better to do this by setting SECURE_PROXY_SSL_HEADER but I am not 100% sure that will not cause other
    # problems, so trying this first and will attempt to set that as a smaller update later.
    # See: https://ubuntu.com/blog/django-behind-a-proxy-fixing-absolute-urls
    scheme = request.scheme
    if scheme == 'http' and request.META.get('HTTP_X_FORWARDED_PROTO') == 'https':
        scheme = 'https'
    return scheme + '://' + get_current_site(request).domain + '/account/add_scope_callback/'

class MyAccountView(EventMixin, ThemedPageMixin, TemplateView):
    template_name = 'roster/my_account.html'

    def get(self, request, *args, **kwargs):
        clusive_user: ClusiveUser
        clusive_user = request.clusive_user
        google_account = None
        bookshare_account = None
        for account in SocialAccount.objects.filter(user=request.user):
            if account.provider == 'google':
                # Google account's `extra_data` contain the user's google email
                google_account = account.extra_data.get('email')
            if account.provider == 'bookshare':
                # For bookshare, uid is the email address registered with Bookshare.
                # Organization is either a name of an organizational account or
                # a single user account
                bookshare_account = {
                    'id': account.uid,
                    'organization_type': account.extra_data.get('organizational', ''),
                    'organization': self.organization_for_display(account),
                }
        self.extra_context = {
            'can_edit_display_name': False,
            'can_edit_email': False,
            'can_edit_password': clusive_user.can_set_password,
            'google_account': google_account,
            'bookshare_account': bookshare_account,
        }
        return super().get(request, *args, **kwargs)

    def organization_for_display(self, account):
        """
        Return an actual organization name, if any.  If the name
        defaulted to one of the generic ones, return None
        """
        org_name = get_organization_name(account)
        return f'({org_name})' if org_name not in GENERIC_BOOKSHARE_ACCOUNT_NAMES else None

    def configure_event(self, event: Event):
        event.page = 'MyAccount'

def remove_social_account(request, *args, **kwargs):
    clusive_user: ClusiveUser
    clusive_user = request.clusive_user

    # Currently, a Google SocialAccount is created for Google SSO, and not for
    # an associated account.  Google SSO users cannot delete the SocialAccount
    # since it is needed for logging into Clusive.  Use the
    # `clusive_user.data_source` to detect this condition (see finish_login()
    # above, where it is set for Google SSO users).
    social_app_name = kwargs.get('provider')
    if clusive_user.data_source == RosterDataSource.GOOGLE and social_app_name == 'google':
        logger.debug('Google SSO user %s cannot remove their google SocialAccount', request.user.username)
        return HttpResponseRedirect(reverse('my_account'))

    # Find the SocialAccount for the user/provider and delete it.
    # 03-Feb-2022:  there should only be one, but Q/A using the 'Sam' login
    # found multiple SocialTokens and SocialAccounts.  To take that into account
    # loop through all the user's SocialAccounts with the given provider.
    social_accounts = SocialAccount.objects.filter(user=request.user, provider=social_app_name)
    for social_account in social_accounts:
        # Deletion and signal based on allauth's DisconnectForm, see github
        # issue, "How to unlink an account from a social auth provider?":
        # https://github.com/pennersr/django-allauth/issues/814
        social_account.delete()
        request.session.pop('bookshare_connected', None)
        request.session.pop('bookshare_search_metadata', None)
        messages.info(request, "Removed Bookshare account.")
        signals.social_account_removed.send(
            sender=SocialAccount, request=request, socialaccount=social_account
        )
    if social_accounts.count() == 0:
        logger.debug('User %s does not have a %s account', request.user.username, social_app_name)

    return HttpResponseRedirect(reverse('my_account'))
