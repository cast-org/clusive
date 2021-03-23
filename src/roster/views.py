import csv
import json
import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, get_user_model
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
from roster import csvparser
from roster.csvparser import parse_file
from roster.forms import PeriodForm, SimpleUserCreateForm, UserEditForm, UserRegistrationForm, \
    AccountRoleForm, AgeCheckForm, ClusiveLoginForm
from roster.models import ClusiveUser, Period, PreferenceSet, Roles, ResearchPermissions

logger = logging.getLogger(__name__)


def guest_login(request):
    clusive_user = ClusiveUser.make_guest()
    login(request, clusive_user.user)
    return redirect('dashboard')


class LoginView(auth_views.LoginView):
    template_name='roster/login.html'
    form_class = ClusiveLoginForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get('form').errors:
            for err in context.get('form').errors.as_data().get('__all__'):
                if err.code == 'email_validate':
                    context['email_validate'] = True
        return context


class SignUpView(EventMixin, CreateView):
    template_name='roster/sign_up.html'
    model = User
    form_class = UserRegistrationForm

    def post(self, request, *args, **kwargs):
        self.role = kwargs['role']
        self.current_clusive_user = request.clusive_user
        self.current_site = get_current_site(request)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # Don't call super since that would save the target model, which we might not want.
        target : User
        target = form.instance
        if not self.role in ['TE', 'PA', 'ST']:
            raise PermissionError('Invalid role')
        user: User
        if self.current_clusive_user:
            # There is a logged-in (presumably Guest) user.
            # Update the ClusiveUser and User objects based on the form target.
            clusive_user: ClusiveUser
            clusive_user = self.current_clusive_user
            logger.debug('Upgrading %s from guest to %s', clusive_user, self.role)
            clusive_user.role = self.role
            clusive_user.permission = ResearchPermissions.PERMISSIONED
            clusive_user.save()
            user = clusive_user.user
            user.username = target.username
            user.first_name = target.first_name
            user.set_password(form.cleaned_data["password1"])
            user.email = target.email
            user.save()
            login(self.request, user) # Need to login again since User object has changed.
            send_validation_email(self.current_site, clusive_user)
        else:
            # This is a new user.  Save the form target User object, and create a ClusiveUser.
            user = target
            user.set_password(form.cleaned_data["password1"])
            user.save()
            clusive_user = ClusiveUser.objects.create(user=user,
                                       role=self.role,
                                       permission=ResearchPermissions.PERMISSIONED,
                                       anon_id=ClusiveUser.next_anon_id())
            send_validation_email(self.current_site, clusive_user)
        return HttpResponseRedirect(reverse('validate_sent', kwargs={'user_id' : user.id}))

    def configure_event(self, event: Event):
        event.page = 'Register'


class ValidateSentView(View):
    template_name = 'roster/validate_sent.html'

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs.get('user_id'))
        context = {
            'user_id': user.id,
            'email': user.email,
            'status': 'sent',
        }
        return render(request, self.template_name, context)


class ValidateResendView(TemplateView):
    template_name = 'roster/validate_sent.html'

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs.get('user_id'))
        clusive_user = ClusiveUser.objects.get(user=user)
        if clusive_user.unconfirmed_email:
            send_validation_email(get_current_site(request), clusive_user)
            status = 'resent'
        else:
            logger.warning('Skipping email sending; already activated user %s', clusive_user)
            status = 'unneeded'
        context = {
            'user_id': user.id,
            'email': user.email,
            'status': status,
        }
        return render(request, self.template_name, context)


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


class SignUpRoleView(EventMixin, FormView):
    form_class = AccountRoleForm
    template_name = 'roster/sign_up_role.html'

    def form_valid(self, form):
        role = form.cleaned_data['role']
        if role == 'ST':
            self.success_url = reverse('sign_up_age_check')
        else:
            self.success_url = reverse('sign_up', kwargs={'role': role})
        return super().form_valid(form)

    def configure_event(self, event: Event):
        event.page = 'RegisterRole'


class SignUpAgeCheckView(EventMixin, FormView):
    form_class = AgeCheckForm
    template_name = 'roster/sign_up_age_check.html'

    def form_valid(self, form):
        logger.debug("of age: %s", repr(form.cleaned_data['of_age']))
        if form.cleaned_data['of_age'] == 'True':
            self.success_url = reverse('sign_up', kwargs={'role': 'ST'})
        else:
            self.success_url = reverse('sign_up_ask_parent')
        return super().form_valid(form)

    def configure_event(self, event: Event):
        event.page = 'RegisterAge'


class SignUpAskParentView(EventMixin, TemplateView):
    template_name = 'roster/sign_up_ask_parent.html'

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
    logger.info("client_side_prefs_change message received")    
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


class ManageView(LoginRequiredMixin, EventMixin, TemplateView):
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


class ManageCreateUserView(LoginRequiredMixin, EventMixin, CreateView):
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
        cu = ClusiveUser.objects.create(user=target,
                                   role=Roles.STUDENT,
                                   permission=ResearchPermissions.GUEST)
        # Add user to the Period
        self.period.users.add(cu)
        return super().form_valid(form)

    def configure_event(self, event: Event):
        event.page = 'ManageCreateStudent'


class ManageEditUserView(LoginRequiredMixin, EventMixin, UpdateView):
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


class ManageEditPeriodView(LoginRequiredMixin, EventMixin, UpdateView):
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


class ManageCreatePeriodView(LoginRequiredMixin, EventMixin, CreateView):
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
