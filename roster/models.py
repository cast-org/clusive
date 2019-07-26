from django.db import models
from uuid import uuid4
from django.contrib.auth.models import User

class ClusiveUser(models.Model):
    
    # Django standard user class contains the following fields already
    # - first_name
    # - last_name
    # - username
    # - password
    # - email
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    subject_id = models.CharField(unique=True, default=uuid4, max_length=32)

    # TODO: should this be an enum of states, as per comment 
    # at https://wiki.cast.org/display/CISL/User+model+development?
    permission = models.BooleanField(default=False)        

    # TODO: consider creating a separate "Roles" model to store 
    # roles, and refer to them with a Foreignkey - see comment 
    # about "hacking choices to be dymaic" at https://docs.djangoproject.com/en/2.2/ref/models/fields/#choices
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