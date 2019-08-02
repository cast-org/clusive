from django.db import models
from uuid import uuid4
from django.contrib.auth.models import User

class Site(models.Model):
    name = models.CharField(max_length=100)
    anon_id = models.CharField(unique=True, default=uuid4, max_length=36)
    # TODO: is this an address field? Should it be managed as such?
    location = models.TextField(max_length=500)

    # TODO: should these three be restricted by choices?
    language_code = models.CharField(max_length=2, default='EN')
    country_code = models.CharField(max_length=2, default='US')
    timezone = models.CharField(max_length=30, default='EST')

    def __str__(self):
        return '%s (%s)' % (self.name, self.site_id)

class Period(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    anon_id = models.CharField(unique=True, default=uuid4, max_length=36)

    def __str__(self):
        return '%s (%s)' % (self.name, self.class_id)

class ClusiveUser(models.Model):
    
    # Django standard user class contains the following fields already
    # - first_name
    # - last_name
    # - username
    # - password
    # - email
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    anon_id = models.CharField(unique=True, default=uuid4, max_length=36)

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
        return '%s' % (self.subject_id)