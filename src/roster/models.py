import json
import logging
from datetime import timedelta

from allauth.account.signals import user_signed_up
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property
from mailchimp_marketing import Client
from mailchimp_marketing.api_client import ApiClientError
from multiselectfield import MultiSelectField
from pytz import country_timezones

logger = logging.getLogger(__name__)

# TODO: Should we include timezones other than US + Canada?
available_timezones = sorted(country_timezones('us') + country_timezones('ca'))
available_timezones_friendly = []
for tz in available_timezones:
    tz_friendly = tz.replace("_", " ")
    available_timezones_friendly.append(tz_friendly)

class Site(models.Model):
    name = models.CharField(max_length=100)
    anon_id = models.CharField(max_length=30, unique=True, null=True)

    city = models.CharField(max_length=50, default="")
    state_or_province = models.CharField(max_length=50, default="")
    country = models.CharField(max_length=50, default="")

    TIMEZONE_CHOICES = list(zip(available_timezones, available_timezones_friendly))

    timezone = models.CharField(max_length=30, default='America/New_York', choices=TIMEZONE_CHOICES)

    def __str__(self):
        return '%s (%s)' % (self.name, self.anon_id)


class RosterDataSource:
    CLUSIVE = 'C'
    GOOGLE = 'G'

    CHOICES = [
        (CLUSIVE, "Created in Clusive"),
        (GOOGLE, "Google Classroom"),
    ]


class Period(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name='Class name')
    anon_id = models.CharField(max_length=30, unique=True, null=True, verbose_name='Anonymous identifier')
    data_source = models.CharField(max_length=4, choices=RosterDataSource.CHOICES, default=RosterDataSource.CLUSIVE)
    external_id = models.CharField(max_length=100, null=True, blank=True, verbose_name='External ID')

    @cached_property
    def student_count(self):
        """Query the number of students in this Period. Use property rather than function call for caching."""
        logger.debug('Querying for number of students')
        return ClusiveUser.objects.filter(periods=self, role=Roles.STUDENT).count()

    def __str__(self):
        return '%s (%s)' % (self.name, self.anon_id)


class Roles:
    GUEST = 'GU'
    STUDENT = 'ST'
    PARENT = 'PA'
    TEACHER = 'TE'
    RESEARCHER = 'RE'
    ADMIN = 'AD'
    UNKNOWN = 'UN'

    ROLE_CHOICES = [
        (GUEST, 'Guest'),
        (STUDENT, 'Student'),
        (PARENT, 'Parent'),
        (TEACHER, 'Teacher'),
        (RESEARCHER, 'Researcher'),
        (ADMIN, 'Admin'),
        (UNKNOWN, 'Unknown')
    ]

    @classmethod
    def display_name(cls, role):
        return [item[1] for item in Roles.ROLE_CHOICES if item[0] == role][0]


class ResearchPermissions:
    PERMISSIONED = 'PE'
    PENDING = 'PD'
    DECLINED = 'DC'
    WITHDREW = 'WD'
    SELF_CREATED = 'SC'
    PARENT_CREATED = 'PC'
    TEACHER_CREATED = 'TC'
    TEST_ACCOUNT = 'TA'
    GUEST = 'GU'

    CHOICES = [
        (PERMISSIONED, 'Permissioned'),
        (PENDING, 'Pending'),
        (DECLINED, 'Declined'),
        (WITHDREW, 'Withdrew'),
        (SELF_CREATED, 'Self-created account'),
        (PARENT_CREATED, 'Parent-created account'),
        (TEACHER_CREATED, 'Teacher-created account'),
        (TEST_ACCOUNT, 'Test account'),
        (GUEST, 'Guest account')
    ]

    RESEARCHABLE = [
        PERMISSIONED,
        SELF_CREATED,
        TEACHER_CREATED,
        PARENT_CREATED]


class EducationLevels:
    LOWER_ELEMENTARY = 'LE'
    UPPER_ELEMENTARY = 'UE'
    MIDDLE_SCHOOL = 'MS'
    HIGH_SCHOOL = 'HS'

    CHOICES = [
        (LOWER_ELEMENTARY, 'Lower Elementary'),
        (UPPER_ELEMENTARY, 'Upper Elementary'),
        (MIDDLE_SCHOOL, 'Middle School'),
        (HIGH_SCHOOL, 'High School'),
    ]

class LibraryViews:
    ALL = 'all'
    PUBLIC = 'public'
    MINE = 'mine'
    STARRED = 'starred'
    PERIOD = 'period'

    CHOICES = [
        (ALL, 'All readings'),
        (PUBLIC, 'Public readings'),
        (MINE, 'Uploaded readings'),
        (STARRED, 'Starred readings'),
        (PERIOD, 'Period assignments')
    ]

    @staticmethod
    def display_name_of(view):
        try:
            return next(x[1] for x in LibraryViews.CHOICES if x[0] == view)
        except StopIteration:
            logger.warning('Found no name for library view ' + view)
            return None

class LibraryStyles:
    BRICKS = 'bricks'
    GRID = 'grid'
    LIST = 'list'

    CHOICES = [
        (BRICKS, 'bricks'),
        (GRID, 'grid'),
        (LIST, 'list'),
    ]

class LibrarySort:
    TITLE = 'title'
    AUTHOR = 'author'
    RECENT = 'recent'

    CHOICES = [
        (TITLE, 'title'),
        (AUTHOR, 'author'),
        (RECENT, 'recent'),
    ]


class StudentActivitySort:
    NAME = 'name'
    TIME = 'time'
    COUNT = 'count'

    CHOICES = [
        (NAME, 'name'),
        (TIME, 'time'),
        (COUNT, 'count'),
    ]

class TransformTool:
    SIMPLIFY = 'simplify'
    TRANSLATE = 'translate'
    PICTURES = 'pictures'

    CHOICES = [
        (SIMPLIFY, 'simplify'),
        (TRANSLATE, 'translate'),
        (PICTURES, 'pictures'),
    ]

def check_valid_choice(choices, value):
    try:
        next(x[1] for x in choices if x[0] == value)
        return True
    except StopIteration:
        logger.warning('Found no match for choice ' + value)
        return False

class ClusiveUser(models.Model):
    guest_serial_number = 0
    anon_id_serial_number = 0

    # Django standard user class contains the following fields already
    # - first_name
    # - username
    # - password
    # - email
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Anonymous ID for privacy protection when logging activities for research
    anon_id = models.CharField(max_length=30, unique=True, null=True)

    data_source = models.CharField(max_length=4, choices=RosterDataSource.CHOICES, default=RosterDataSource.CLUSIVE)
    external_id = models.CharField(max_length=100, null=True, blank=True, verbose_name='External ID')

    # If True, user cannot log in until they have confirmed their email.
    unconfirmed_email = models.BooleanField(default=False)

    # List of all class periods the user is part of
    periods = models.ManyToManyField(Period, blank=True, related_name='users')

    # Which period will be shown by default, eg in library or manage rosters view
    current_period = models.ForeignKey(Period, null=True, blank=True, on_delete=models.SET_NULL)

    # Which view of the dashboard 'Popular Reads' panel the user last viewed. This choice is persistent.
    dashboard_popular_view = models.CharField(max_length=10, default="",
                                              choices=DashboardPopularViews.CHOICES)

    # Which view of the library page the user last viewed. This choice is persistent.
    library_view = models.CharField(max_length=10, default=LibraryViews.PERIOD,
                                    choices=LibraryViews.CHOICES)

    # How the library was sorted most recently. This choice is persistent.
    library_sort = models.CharField(max_length=10, default=LibrarySort.TITLE,
                                    choices=LibrarySort.CHOICES)

    # What layout to use for the library cards. This choice is persistent.
    library_style = models.CharField(max_length=10, default=LibraryStyles.BRICKS,
                                     choices=LibraryStyles.CHOICES)

    # How many days worth of data are shown in the 'Student activity' display. 0 means no limit.
    student_activity_days = models.SmallIntegerField(default=0)

    # How the user has chosen to sort the 'Student activity' display. This choice is persistent.
    student_activity_sort = models.CharField(max_length=10, default=StudentActivitySort.NAME,
                                             choices=StudentActivitySort.CHOICES)

    # How the user has chosen to simplify or translate text
    transform_tool = models.CharField(max_length=10, default=TransformTool.TRANSLATE,
                                      choices=TransformTool.CHOICES)

    # Levels taught. Asked of teachers at registration.
    education_levels = MultiSelectField(choices=EducationLevels.CHOICES,
                                        verbose_name='Education levels',
                                        blank=True, default=[])

    # Site that this user is connected to. Although users can have multiple Periods,
    # these are generally assumed to be all part of one Site.
    # If this assumption is changed, then the Manage pages will need updates
    # to allow users to manage their different Sites.
    def get_site(self):
        period = self.current_period or self.periods.first()
        if period:
            return period.site
        # If the user can manage periods (Parent or Teacher)
        # and doesn't currently have a Site, we create
        # a personal one for them at this point
        if self.can_manage_periods:
            personal_site_name = "user-" + str(self.user.id) + "-personal-site"
            personal_site = Site(name=personal_site_name)
            personal_site.save()
            return personal_site
        else:
            return None

    permission = models.CharField(
        max_length=2,
        choices=ResearchPermissions.CHOICES,
        default=ResearchPermissions.TEST_ACCOUNT
    )

    role = models.CharField(
        max_length=2,
        choices=Roles.ROLE_CHOICES,
        default=Roles.GUEST
    )

    @property
    def is_permissioned(self):
        return self.permission in ResearchPermissions.RESEARCHABLE

    @property
    def is_registered(self):
        return self.role and self.role != Roles.GUEST

    @property
    def can_set_password(self):
        """True if this user can change their own password."""
        return self.role and self.role != Roles.GUEST and self.data_source == RosterDataSource.CLUSIVE

    @property
    def can_upload(self):
        """True if this user can upload content."""
        return self.role and self.role != Roles.GUEST

    @property
    def can_manage_periods(self):
        """True if this user can edit the users and content connected to Periods they are in."""
        return self.role and (self.role == Roles.TEACHER or self.role == Roles.PARENT)

    def get_preference(self, pref):
        pref, created = Preference.objects.get_or_create(user=self, pref=pref)
        return pref

    def set_preference(self, pref, value):
        pref, created = Preference.objects.get_or_create(user=self, pref=pref)
        pref.typed_value = value
        pref.save()
        return pref

    def get_preferences(self):
        return Preference.objects.filter(user=self)

    def get_preferences_dict(self):
        """Build and return a dictionary of preference names to preference values for this user."""
        return {p.pref: p.typed_value for p in (self.get_preferences())}

    def delete_preferences(self):
        prefs = Preference.objects.filter(user=self)
        logger.info("deleting preferences for %s", self.user.username);
        return prefs.delete()

    # adopts a preference set; does not log a preference change event right now
    def adopt_preferences_set(self, prefset_name):
        logger.info("trying to adopt preference set named %s for %s" % (prefset_name, self.user.username))
        try:
            prefs_set = PreferenceSet.objects.get(name=prefset_name)

            desired_prefs = json.loads(prefs_set.prefs_json)

            for pref_key in desired_prefs:
                pref_val = desired_prefs[pref_key]
                preference = self.get_preference(pref_key)
                if(preference.value != pref_val):
                    preference.value = pref_val
                    preference.save()

        except PreferenceSet.DoesNotExist:
            logger.error("preference set named %s not found", prefset_name)

    def set_simplification_tool(self, choice):
        if self.transform_tool != choice:
            self.transform_tool = choice
            self.save()

    @classmethod
    def from_request(cls, request):
        try:
            return ClusiveUser.objects.get(user=request.user)
        except ClusiveUser.DoesNotExist:
            logger.error("Expected ClusiveUser, got %s", request.user)

    @classmethod
    def next_guest_username(cls):
        # Loop until we find an unused username. (should only require looping the first time)
        while True:
            cls.guest_serial_number += 1
            uname = 'guest%d' % (cls.guest_serial_number)
            if not User.objects.filter(username=uname).exists():
                return uname

    @classmethod
    def next_anon_id(cls):
        # Loop until we find an unused ID. (should only require looping the first time)
        while True:
            cls.anon_id_serial_number += 1
            anon_id = 's%d' % cls.anon_id_serial_number
            if not ClusiveUser.objects.filter(anon_id=anon_id).exists():
                return anon_id

    @classmethod
    def add_defaults(cls, properties):
        """Add default values to a partially-specified ClusiveUser properties dict.
        """
        if not properties.get('role'):
            properties['role'] = Roles.STUDENT
        if not properties.get('password'):
            properties['password'] = User.objects.make_random_password()
        if not properties.get('anon_id'):
            properties['anon_id'] = cls.next_anon_id()
        if not properties.get('permission'):
            properties['permission'] = ResearchPermissions.TEST_ACCOUNT
        return properties

    @classmethod
    def check_uniqueness_errors(cls, properties):
        """Check if a user with the given properties could be created.

        Properties must be a dict with fields like those of a ClusiveUser.
        The username and anon_id fields will be checked for uniqueness.
        In the future other sanity checks may also be performed.

        Returns an error message as a string, or None if everything looks ok.
        """
        username = properties.get('username')
        anon_id = properties.get('anon_id')
        if username and User.objects.filter(username=username).exists():
            return "Username already exists"
        if anon_id and ClusiveUser.objects.filter(anon_id=anon_id).exists():
            return "Anon_id already exists"
        return None

    @classmethod
    def create_from_properties(cls, props):
        django_user = User.objects.create_user(username=props.get('username'),
                                               first_name=props.get('first_name'),
                                               password=props.get('password'),
                                               email=props.get('email'))
        clusive_user = ClusiveUser.objects.create(user=django_user,
                                                  role=props.get('role'),
                                                  permission=props.get('permission'),
                                                  anon_id=props.get('anon_id'),
                                                  data_source=props.get('data_source', RosterDataSource.CLUSIVE),
                                                  external_id=props.get('external_id', ''))
        site_name = props.get('site', None)
        period_name = props.get('period', None)
        if site_name and period_name:
            period = Period.objects.get(site__name=site_name, name=period_name)
            clusive_user.periods.set([period])
        clusive_user.save()
        return clusive_user

    @classmethod
    def make_guest(cls):
        uname = cls.next_guest_username()
        logger.info("Creating guest user: %s", uname)
        django_user = User.objects.create_user(username=uname,
                                               first_name='Guest ' + str(cls.guest_serial_number))
        clusive_user = ClusiveUser.objects.create(user=django_user,
                                                  role=Roles.GUEST,
                                                  permission=ResearchPermissions.GUEST,
                                                  anon_id=cls.next_anon_id())
        return clusive_user

    def __str__(self):
        return '%s' % (self.anon_id)

# This is the current recommended way to ensure additional code is run after
# the initial creation of an object; 'created' is True only on the save() from
# initial creation
@receiver(post_save, sender=ClusiveUser)
def set_default_preferences(sender, instance, created, **kwargs):
    if(created):
        logger.info("New user created, setting preferences to 'default' set")
        instance.adopt_preferences_set('default_display')
        instance.adopt_preferences_set('default_reading_tools')

# The signal is sent from django-allauth, and indicates the first time that a
# user has connected a social account to their local account using another
# app's single-sign-on (e.g, Google), but before they are fully logged in.
# Check to see if the associated User has an associated ClusiveUser; and,
# if not, create one.
@receiver(user_signed_up)
def add_clusive_user_for_sociallogin(sender, **kwargs):
    django_user = kwargs['sociallogin'].user
    try:
        clusive_user = ClusiveUser.objects.get(user=django_user)
    except ClusiveUser.DoesNotExist:
        logger.info("New social user, attaching new ClusiveUser")
        clusive_user = ClusiveUser.objects.create(user=django_user,
                                                  role=Roles.UNKNOWN,
                                                  permission=ResearchPermissions.GUEST,
                                                  anon_id=ClusiveUser.next_anon_id())


class Preference (models.Model):
    """Store a single user preference setting."""

    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)

    pref = models.CharField(max_length=32, db_index=True)

    value = models.CharField(max_length=64, null=True)

    @property
    def typed_value(self):
        """Returns the value as its actual type - string, int, float, or boolean"""
        return self.convert_from_string(self.value)

    @typed_value.setter
    def typed_value(self, newval):
        self.value = str(newval)

    @classmethod
    def convert_from_string(cls, val):
        """Converts a string value to array, boolean, int, float, or string depending what it looks like."""

        if val is None:
            return None

        # Empty array as string
        if len(val)>1 and val[0] == "[" and val[1] == "]":
            return []

        # Array of strings stored as string
        if len(val)>1 and val[0] == "[" and val[-1] == "]":
            return [x.strip()[1:-1] for x in val[1:-1].split(',')]

        # Booleans
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False

        # Numbers and Strings
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                # Otherwise string type.
                return val

    @classmethod
    def get_theme_for_user(cls, user: ClusiveUser):
        pref = cls.objects.filter(user=user, pref='fluid_prefs_contrast').first() if user else None
        return pref.value if pref else 'default'

    @classmethod
    def get_glossary_pref_for_user(cls, user: ClusiveUser):
        pref = cls.objects.filter(user=user, pref='cisl_prefs_glossary').first() if user else None
        return pref.typed_value if pref else True

    def __str__(self):
        return 'Pref:%s/%s=%s' % (self.user, self.pref, self.value)

class PreferenceSet(models.Model):
    """Store a set of preference keys and values as a JSON string"""

    name = models.CharField(max_length=32)
    description = models.CharField(max_length=256)
    prefs_json = models.TextField()

    @classmethod
    def get_json(cls, name):
        """Return JSON for the preferences in the PreferenceSet with the given name."""
        prefs_set = cls.objects.get(name=name)
        return json.loads(prefs_set.prefs_json)

    def __str__(self):
        return 'PreferenceSet:%s' % (self.name)


class UserStats (models.Model):
    """
    Store some auxilliary data about ClusiveUser's behavior.
    Exactly what will go in here is still somewhat up in the air.
    Should be useful for dashboard display once we get there.
    """

    user = models.OneToOneField(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)
    # Total number of login sessions for this user
    logins = models.PositiveIntegerField(default=0)
    # Number of times opening a book for reading
    reading_views = models.PositiveIntegerField(default=0)
    # Total active time using Clusive
    active_duration = models.DurationField(null=True)

    class Meta:
        verbose_name = 'user stats'
        verbose_name_plural = 'user stats'

    @classmethod
    def update_stats_for_event(cls, event):
        logger.debug('Analyzing event: %s', event)
        if event.type == 'VIEW_EVENT' \
                 and event.action == 'VIEWED' \
                 and event.page == 'Reading':
            logger.debug('  Found stats event')
            stats = cls.for_clusive_user(event.actor)
            stats.reading_views += 1
            stats.save()

    @classmethod
    def for_clusive_user(cls, clusive_user: ClusiveUser):
        (obj, created) = cls.objects.get_or_create(user=clusive_user)
        if created:
            logger.debug('Created new UserStats object for %s', clusive_user)
        return obj

    @classmethod
    def add_active_time(cls, clusive_user: ClusiveUser, duration):
        stats = cls.for_clusive_user(clusive_user)
        if stats.active_duration is None:
            stats.active_duration = timedelta()
        stats.active_duration += duration
        stats.save()

    @classmethod
    def add_login(cls, clusive_user: ClusiveUser):
        stats = cls.for_clusive_user(clusive_user)
        stats.logins += 1
        stats.save()


class MailingListMember (models.Model):
    """
    Email automation integration status;
    Records without a send_completion_date have not been synchronized.
    All Users have successfully been self added and email validated.
    Periodically the user information will be synchronized with MailChimp.
    """
    user = models.OneToOneField(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)
    sync_date = models.DateTimeField(null=True, blank=True)
    failures = models.PositiveSmallIntegerField(default=0)

    MAX_FAILURES = 3  # How many times we're allowed to fail before giving up.

    def update_sync_date(self):
        self.sync_date = timezone.now()
        self.save()

    @classmethod
    def get_members_to_sync(cls):
        members_to_sync = cls.objects.filter(sync_date=None)
        return members_to_sync

    @classmethod
    def synchronize_user_emails(cls):
        messages = []
        members_to_synch = cls.get_members_to_sync()

        if members_to_synch and settings.MAILCHIMP_API_KEY and settings.MAILCHIMP_SERVER \
                and settings.MAILCHIMP_EMAIL_LIST_ID:

            # set up the mailchimp connection
            mailchimp = Client()
            mailchimp.set_config({
                "api_key": settings.MAILCHIMP_API_KEY,
                "server": settings.MAILCHIMP_SERVER
            })

            # loop through all users that have not been synchronized
            member: MailingListMember
            for member in members_to_synch:
                member_info = {
                    "email_address": member.user.user.email,
                    "status": "subscribed",
                    "merge_fields": {
                        "FNAME": member.user.user.first_name,
                        "MMERGE5": member.user.get_role_display()
                    }
                }
                try:
                    response = mailchimp.lists.add_list_member(settings.MAILCHIMP_EMAIL_LIST_ID, member_info)
                    logger.debug("response: %s", response)
                    member.update_sync_date()
                    messages.append('Added: %s' % member.user.user.email)
                except ApiClientError as error:
                    member.failures += 1
                    if member.failures >= cls.MAX_FAILURES:
                        member.update_sync_date()
                        messages.append('Hard failure: %s (%s)' % (member.user.user.email, error.text))
                    else:
                        member.save()
                        messages.append('Soft failure #%d: %s (%s)' % (member.failures, member.user.user.email, error.text))
                    logger.error("A mailchimp subscribe exception occurred (%d failures so far): %s",
                                 member.failures, error.text)
        else:
            for member in members_to_synch:
                member_info = {
                    "email_address": member.user.user.email,
                    "status": "subscribed",
                    "merge_fields": {"FNAME": member.user.user.first_name,
                                     "MMERGE5": member.user.get_role_display()}
                }
                messages.append('Added: %s' % member.user.user.email)
                logger.debug('Would send to MailChimp: %s', member_info)
        return messages
