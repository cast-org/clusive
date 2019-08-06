from django.db import models
from django.contrib.auth.models import User
from pytz import country_timezones

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

class ClusiveUser(models.Model):
    
    # Django standard user class contains the following fields already
    # - first_name
    # - last_name
    # - username
    # - password
    # - email
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    anon_id = models.CharField(max_length=30, unique=True, null=True)

    # TODO: should this be an enum of states, as per comment 
    # at https://wiki.cast.org/display/CISL/User+model+development?
    permission = models.BooleanField(default=False)        

    periods = models.ManyToManyField(Period)

    # TODO: consider creating a separate "Roles" model to store 
    # roles, and refer to them with a Foreignkey - see comment 
    # about "hacking choices to be dynamic" at https://docs.djangoproject.com/en/2.2/ref/models/fields/#choices
    #

    GUEST = 'GU'
    STUDENT = 'ST'
    TEACHER = 'TE'
    RESEARCHER = 'RE'
    ADMIN = 'AD'

    ROLE_CHOICES = [
        (GUEST, 'Guest'),
        (STUDENT, 'Student'),
        (TEACHER, 'Teacher'),
        (RESEARCHER, 'Researcher'),        
        (ADMIN, 'Admin')
    ]

    role = models.CharField(
        max_length=2,
        choices=ROLE_CHOICES,
        default=GUEST
    )    

    def __str__(self):
        return '%s' % (self.anon_id)