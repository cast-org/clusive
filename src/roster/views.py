import csv
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, get_user_model, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, UpdateView, CreateView, FormView


from eventlog.models import Event
from eventlog.signals import preference_changed
from eventlog.views import EventMixin
from messagequeue.models import Message, client_side_prefs_change
from pages.views import ThemedPageMixin
from roster import csvparser
from roster.csvparser import parse_file
from roster.forms import PeriodForm, SimpleUserCreateForm, UserEditForm, UserRegistrationForm, \
    AccountRoleForm, AgeCheckForm, ClusiveLoginForm
from roster.models import ClusiveUser, Period, PreferenceSet, Roles, ResearchPermissions, MailingListMember
from roster.signals import user_registered

from allauth.socialaccount.models import SocialToken, SocialApp
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from django.utils.crypto import get_random_string
from datetime import timedelta
import requests
from urllib.parse import urlencode

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

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


@staff_member_required
def upload_csv(request):
    template = 'roster/upload_csv.html'
    context = {'fields': csvparser.FIELDS, 'title': 'Bulk add users'}

    if request.method == "GET":
        # First render; just show the form.
        return render(request, template, context)

    # POST means a file was uploaded.
    dry_run = request.POST.get('test')
    if dry_run:
        messages.warning(request, 'Testing CSV file only - database will not be changed')

    if not request.FILES:
        messages.error(request, 'No file uploaded')
    else:
        csv_file = request.FILES['file']
        try:
            csvreader = csv.DictReader(chunk.decode() for chunk in csv_file)
            result = parse_file(csvreader)
            context = result
            context['dry_run'] = dry_run

            if not context['errors'] and not dry_run:
                try:
                    for u in result['users']:
                        ClusiveUser.create_from_properties(u)
                    messages.info(request, 'Users created')
                except Exception as e:
                    context['errors'].append('Database error: %s' % e)
                    messages.error(request, 'Error during creation of users - some may have been created')

        except csv.Error as e:
            context['errors'] = ["CSV formatting error: %s" % e]
            context['sites'] = {}
            context['users'] = {}

        if context['errors']:
            messages.error(request, 'Problems found')
        else:
            messages.info(request, 'File looks good')

    return render(request, template, context)


class ManageView(LoginRequiredMixin, EventMixin, ThemedPageMixin, TemplateView):
    template_name = 'roster/manage.html'
    periods = None
    current_period = None

    def get(self, request, *args, **kwargs):
        user = request.clusive_user
        if not user.can_manage_periods:
            self.handle_no_permission()
        if self.periods is None:
            self.periods = user.periods.all()
        if kwargs.get('period_id'):
            self.current_period = get_object_or_404(Period, pk=kwargs.get('period_id'))
            # Make sure you can only edit a Period you are in.
            if self.current_period not in self.periods:
                self.handle_no_permission()
        if self.current_period is None:
            if user.current_period:
                self.current_period = user.current_period
            elif self.periods:
                self.current_period = self.periods[0]
            # else:
            #     # No periods.  If this case actually happens, should have a better error message.
            #     self.handle_no_permission()
        if self.current_period != user.current_period and self.current_period != None:
            user.current_period = self.current_period
            user.save()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['periods'] = self.periods
        context['current_period'] = self.current_period
        if self.current_period != None:
            context['students'] = self.make_student_info_list()
            context['period_name_form'] = PeriodForm(instance=self.current_period)
            logger.debug('Students: %s', context['students'])
        return context

    def make_student_info_list(self):
        students = self.current_period.users.filter(role=Roles.STUDENT).order_by('user__first_name')
        return [{
            'info': s.user,
        } for s in students]

    def configure_event(self, event: Event):
        event.page = 'Manage'


class ManageCreateUserView(LoginRequiredMixin, EventMixin, ThemedPageMixin, CreateView):
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
        self.check_access_token()
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

class ManageEditUserView(LoginRequiredMixin, EventMixin, ThemedPageMixin, UpdateView):
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
        new_pw = form.cleaned_data['password']
        if new_pw:
            target.set_password(new_pw)
            target.save()
        return super().form_valid(form)

    def configure_event(self, event: Event):
        event.page = 'ManageEditStudent'


class ManageEditPeriodView(LoginRequiredMixin, EventMixin, ThemedPageMixin, UpdateView):
    model = Period
    form_class = PeriodForm
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


class ManageCreatePeriodView(LoginRequiredMixin, EventMixin, ThemedPageMixin, CreateView):
    model = Period
    form_class = PeriodForm
    template_name = 'roster/manage_create_period.html'

    def get_form(self, form_class=None):
        instance=Period(site=self.clusive_user.get_site())
        kwargs = self.get_form_kwargs()
        kwargs['instance'] = instance
        return PeriodForm(**kwargs)

    def dispatch(self, request, *args, **kwargs):
        cu = request.clusive_user
        if not cu.can_manage_periods:
            self.handle_no_permission()
        self.clusive_user = cu
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('manage', kwargs={'period_id': self.object.id})

    def form_valid(self, form):
        result = super().form_valid(form)
        # Add current user to the new Period
        self.object.users.add(self.clusive_user)
        return result

    def configure_event(self, event: Event):
        event.page = 'ManageCreatePeriod'

def finish_login(request):
    if request.user.is_staff:
        return HttpResponseRedirect('/admin')
    clusive_user = ClusiveUser.from_request(request)
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

    def get(self, request):
        logger.debug('Sync mailing list request received')
        MailingListMember.synchronize_user_emails()
        return JsonResponse({'success': 1})

class GoogleCoursesView(LoginRequiredMixin, ThemedPageMixin, TemplateView):
    # TODO Move the parts that have to do with getting greater scope access
    # to ManageCreatePeriodView, and have that oauth2 sequence trigger from
    # there.  This should be for displaying the Google course list response
    template_name = 'roster/manage_create_period.html'
    model = Period
    form_class = PeriodForm
    provider = 'google'
    classroom_scopes = 'https://www.googleapis.com/auth/classroom.courses.readonly https://www.googleapis.com/auth/classroom.rosters.readonly'
    auth_parameters = urlencode({
        'provider': provider,
        'scopes': classroom_scopes,
        'authorization': 'http://accounts.google.com/o/oauth2/v2/auth?'
    })

    def get(self, request, *args, **kwargs):
        db_access = OAuth2Database()
        user_credentials = self.make_credentials(request.user, self.classroom_scopes, db_access)
        service = build('classroom', 'v1', credentials=user_credentials)
        try:
            results = service.courses().list(pageSize=10).execute()
        except HttpError as e:
            if e.status_code == 403:
                url = reverse('add_scope_access') + '?' + self.auth_parameters
                return HttpResponseRedirect(url)
            else:
                raise
        courses = results.get('courses', []);
        logger.debug('There are (%s) Google courses', len(courses))
        for course in courses:
            logger.debug('- %s', course['name'])
        return HttpResponseRedirect(reverse('manage_create_period'))

    def make_credentials(self, user, scopes, db_access):
        client_info = db_access.retrieve_client_info(self.provider)
        access_token = db_access.retrieve_access_token(user, self.provider)
        return Credentials(access_token.token,
                            refresh_token=access_token.token_secret,
                            client_id=client_info.client_id,
                            client_secret=client_info.secret,
                            token_uri='https://accounts.google.com/o/oauth2/token')

########################################
#
# Functions for adding scope(s) workflow
# TODO: turn into a View?

class OAuth2Database(object):

    def retrieve_client_info(self, provider):
        client_info = SocialApp.objects.filter(provider=provider).first()
        return client_info

    def retrieve_access_token(self, user, provider):
        # TODO: Check whether use of first() is always correct.  It assumes
        # there is only ever one access token per user/provider combo.
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
    state = get_random_string(12)
    request.session['oauth2_state'] = state

    client_info = OAuth2Database().retrieve_client_info(provider)
    parameters = urlencode({
        'client_id': client_info.client_id,
        'response_type': 'code',
        'scope': new_scopes,
        'include_granted_scopes': 'true',
        'state': state,
        'redirect_uri': 'http://localhost:8000/account/add_scope_callback/'
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
    # Note: for production, replace the `redirect_uri` with the official uri
    client_info = dbAccess.retrieve_client_info('google')
    logger.debug('Token request to provider for larger scope access')
    resp = requests.request(
        'POST',
        'https://accounts.google.com/o/oauth2/token',
        data={
            'redirect_uri': 'http://localhost:8000/account/add_scope_callback/',
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

    # Current assumption is that the request for additional scope access
    # originated from a "get google courses" request, so return to that
    # workflow.  Where to go from here should be more flexible (future
    # work).
    logger.debug('Larger scope access request complete, returning to get_google_courses')
    return HttpResponseRedirect(reverse('get_google_courses'))
