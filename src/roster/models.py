import logging

from django.contrib.auth.models import User
from django.db import models

from django.db.models.signals import post_save
from django.dispatch import receiver

from pytz import country_timezones

import json

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

class Period(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    anon_id = models.CharField(max_length=30, unique=True, null=True)

    def __str__(self):
        return '%s (%s)' % (self.name, self.anon_id)


class Roles:
    GUEST = 'GU'
    STUDENT = 'ST'
    PARENT = 'PA'
    TEACHER = 'TE'
    RESEARCHER = 'RE'
    ADMIN = 'AD'

    ROLE_CHOICES = [
        (GUEST, 'Guest'),
        (STUDENT, 'Student'),
        (PARENT, 'Parent'),
        (TEACHER, 'Teacher'),
        (RESEARCHER, 'Researcher'),
        (ADMIN, 'Admin')
    ]


class ResearchPermissions:
    PERMISSIONED = 'PE'
    PENDING = 'PD'
    DECLINED = 'DC'
    WITHDREW = 'WD'
    TEST_ACCOUNT = 'TA'
    GUEST = 'GU'

    CHOICES = [
        (PERMISSIONED, 'Permissioned'),
        (PENDING, 'Pending'),
        (DECLINED, 'Declined'),
        (WITHDREW, 'Withdrew'),
        (TEST_ACCOUNT, 'Test Account'),
        (GUEST, 'Guest Account')
    ]


class LibraryViews:
    ALL = 'all'
    PUBLIC = 'public'
    MINE = 'mine'
    PERIOD = 'period'

    CHOICES = [
        (ALL, 'All content'),
        (PUBLIC, 'Public content'),
        (MINE, 'My content'),
        (PERIOD, 'Period assignments')
    ]

    @staticmethod
    def display_name_of(view):
        return next(x[1] for x in LibraryViews.CHOICES if x[0] == view)


class ClusiveUser(models.Model):
    
    # Django standard user class contains the following fields already
    # - first_name
    # - last_name
    # - username
    # - password
    # - email
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Anonymous ID for privacy protection when logging activities for research
    anon_id = models.CharField(max_length=30, unique=True, null=True)

    # List of all class periods the user is part of
    periods = models.ManyToManyField(Period, blank=True, related_name='periods')

    # Which period will be shown by default, eg in library or manage rosters view
    current_period = models.ForeignKey(Period, null=True, blank=True, on_delete=models.SET_NULL)

    # Which view of the library page the user last viewed. This choice is persistent.
    library_view = models.CharField(max_length=10, default=LibraryViews.PERIOD,
                                    choices=LibraryViews.CHOICES)

    @property 
    def is_permissioned(self):
        return self.permission == ResearchPermissions.PERMISSIONED

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
    def can_set_password(self):
        return self.role and self.role != Roles.GUEST

    @property
    def can_upload(self):
        return self.role and self.role != Roles.GUEST

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

    guest_serial_number = 0

    @classmethod
    def from_request(cls, request):
        try:
            return ClusiveUser.objects.get(user=request.user)
        except ClusiveUser.DoesNotExist:
            logger.error("Expected ClusiveUser, got %s", request.user)

    @classmethod
    def next_guest_username(cls):
        cls.guest_serial_number += 1
        return 'guest%d' % (cls.guest_serial_number)

    @classmethod
    def add_defaults(cls, properties):
        """Add default values to a partially-specified ClusiveUser properties dict.

        """
        if not properties.get('role'):
            properties['role'] = Roles.STUDENT
        if not properties.get('password'):
            properties['password'] = User.objects.make_random_password()
        if not properties.get('anon_id'):
            properties['anon_id'] = properties['username']
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
        period = Period.objects.get(site__name=props.get('site'), name=props.get('period'))
        django_user = User.objects.create_user(username=props.get('username'),
                                               first_name=props.get('first_name'),
                                               last_name=props.get('last_name'),
                                               password=props.get('password'),
                                               email=props.get('email'))
        clusive_user = ClusiveUser.objects.create(user=django_user,
                                                  role=props.get('role'),
                                                  permission=props.get('permission'),
                                                  anon_id=props.get('anon_id'))
        p = props.get('period')
        if p:
            clusive_user.periods.set([period])
        clusive_user.save()
        return clusive_user

    @classmethod
    def make_guest(cls):
        username = cls.next_guest_username()
        while User.objects.filter(username=username).exists():
            username = cls.next_guest_username()
        logger.info("Creating guest user: %s", username)
        django_user = User.objects.create_user(username=username,
                                               first_name='Guest',
                                               last_name=str(cls.guest_serial_number))
        clusive_user = ClusiveUser.objects.create(user=django_user,
                                                  role=Roles.GUEST,
                                                  permission=ResearchPermissions.GUEST,
                                                  anon_id=username)
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
        instance.adopt_preferences_set('default')

class Preference (models.Model):
    """Store a single user preference setting."""

    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)

    pref = models.CharField(max_length=32, db_index=True)

    value = models.CharField(max_length=32, null=True)

    @property
    def typed_value(self):
        """Returns the value as its actual type - string, int, float, or boolean"""
        return self.convert_from_string(self.value)

    @typed_value.setter
    def typed_value(self, newval):
        self.value = str(newval)

    @classmethod
    def convert_from_string(cls, val):
        """Converts a string value to a boolean, int, float, or string depending what it looks like."""
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return val

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

