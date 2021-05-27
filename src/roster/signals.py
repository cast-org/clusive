import logging

from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.signals import pre_social_login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django.shortcuts import redirect
from django.urls import reverse

from eventlog.models import Event
from roster.models import UserStats, ClusiveUser

logger = logging.getLogger(__name__)


# This signal is sent when a new user completes the registration/validation process.
user_registered = Signal(providing_args=['clusive_user'])


@receiver(user_registered)
def new_registration_watcher(sender, clusive_user, **kwargs):
    logger.debug('Noticed new registration from %s', clusive_user)
    # TODO: Check whether user is self-created; if so, add to table of mailing-list users

@receiver(post_save, sender=Event)
def stats_event_watcher(sender, instance, **kwargs):
    if kwargs['created']:
        UserStats.update_stats_for_event(instance)


@receiver(pre_social_login, sender=SocialLogin)
def auto_connect_google_login(sender, **kwargs):
    """
    Invoked just after a user successfully authenticates via a
    social provider, but before the login is actually processed.
    See https://stackoverflow.com/questions/19354009/django-allauth-social-login-automatically-linking-social-site-profiles-using-th

    If this is a new social account, but email already exists in the database,
    we want to link to that account rather than create a new one (which would fail due to duplication).
    For security reasons, this should only be allowed if the email is verified.
    """
    request = kwargs['request']
    sociallogin = kwargs['sociallogin']

    # Ignore existing social accounts, just do this stuff for new ones
    if sociallogin.is_existing:
        return

    # some social logins don't have an email address, e.g. facebook accounts
    # with mobile numbers only. If we add Facebook login, enable allauth functionality to ask for an email.
    if 'email' not in sociallogin.account.extra_data:
        return

    # check if given email address already exists (match ignoring case)
    try:
        email = sociallogin.account.extra_data['email'].lower()
        existing_user = User.objects.get(email__iexact=email)
    # if it does not, let allauth take care of this new social account
    except User.DoesNotExist:
        return

    # cannot connect to existing account with unverified email - would allow 3rd party to hijack accounts.
    try:
        clusive_user = ClusiveUser.objects.get(user=existing_user)
        if clusive_user.unconfirmed_email:
            messages.error(request, 'Email already in use by unverified account. Please verify your email or contact support.')
            raise ImmediateHttpResponse(redirect(reverse('login')))
    except ClusiveUser.DoesNotExist:
        messages.error(request, 'Cannot log in to staff account with Google ID.')
        raise ImmediateHttpResponse(redirect(reverse('login')))

    # All tests passed; connect this new social login to the existing user
    logger.info('Connecting google user to existing account: %s', existing_user)
    sociallogin.connect(request, existing_user)
