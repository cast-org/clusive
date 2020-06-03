import logging

from django.contrib.auth.models import User
from django.db import models
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


class ClusiveUser(models.Model):
    
    # Django standard user class contains the following fields already
    # - first_name
    # - last_name
    # - username
    # - password
    # - email
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    anon_id = models.CharField(max_length=30, unique=True, null=True)

    periods = models.ManyToManyField(Period, blank=True)

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

    def get_preference(self, pref):
        pref, created = Preference.objects.get_or_create(user=self, pref=pref)
        return pref

    def get_preferences(self):
        return Preference.objects.filter(user=self)

    def delete_preferences(self):
        prefs = Preference.objects.filter(user=self)
        print("deleting preferences", prefs.delete());
        return prefs.delete()

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


class Preference (models.Model):
    """Store a single user preference setting."""

    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)

    pref = models.CharField(max_length=32, db_index=True)

    value = models.CharField(max_length=32, null=True)

    def __str__(self):
        return 'Pref:%s/%s=%s' % (self.user, self.pref, self.value)
