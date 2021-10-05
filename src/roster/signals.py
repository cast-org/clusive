import logging

from allauth.exceptions import ImmediateHttpResponse
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.signals import pre_social_login, social_account_updated
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django.shortcuts import redirect
from django.urls import reverse

from eventlog.models import Event
from roster.models import UserStats, ClusiveUser, ResearchPermissions, MailingListMember

import pdb

logger = logging.getLogger(__name__)


# This signal is sent when a new user completes the registration/validation process.
user_registered = Signal(providing_args=['clusive_user'])


@receiver(user_registered)
def new_registration_watcher(sender, clusive_user, **kwargs):
    if clusive_user.permission == ResearchPermissions.SELF_CREATED:
        new_member = MailingListMember.objects.create(user=clusive_user)
        new_member.save()
        logger.debug('Noticed and added new registration from %s', clusive_user)
    else:
        logger.debug('Ignoring new user, not self-created: %s', clusive_user)


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

@receiver(social_account_updated, sender=SocialLogin)
def update_social_email(sender, **kwargs):
    """
    Used to update SSO User's email if their SocialAccount is updated.
    One of the updates may be the SocialAccount's email address.  That email is
    stored when they first registered with Clusive.  If it has changed Clusive's
    User email and allauth's EmailAddress is synchronized.
    """
    request = kwargs['request']
    social_login = kwargs['sociallogin']

    # If SocialAccount has no email, nothing to update with.
    if 'email' not in social_login.account.extra_data:
        return
    else:
        social_email = social_login.account.extra_data['email'].lower()

    # If no User with the given ID, nothing to synchronize
    try:
        clusive_user = ClusiveUser.objects.get(external_id=social_login.account.uid)
    except ClusiveUser.DoesNotExist:
        return

    # There should not be another User with the new email, unless it's
    # the same User as retrieved via ID.
    try:
        another_user = User.objects.get(email__iexact=social_email)
        if another_user != clusive_user.user:
            logger.debug('Attempt to update email for %s to %s, but %s already has that email',
                clusive_user.user.first_name,
                social_email,
                another_user.first_name
            )
            return
    except User.DoesNotExist:
        # No other User has `social_email` as their email -- good.
        logger.info('While checking update email for %s, no other Clusive user has that email', social_email)

    # Update
    pdb.set_trace()
    if clusive_user.user.email.lower() != social_email:
        email_address = EmailAddress.objects.get(user_id=clusive_user.user.id)
        clusive_user.user.email = social_email
        clusive_user.user.save()
        email_address.email = social_email
        email_address.save()
