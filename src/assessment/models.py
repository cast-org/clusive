import logging

from django.db import models
from django.utils import timezone

from library.models import Book
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)

class AffectiveCheck:
    
    ANNOYED = 'annoyed'
    BORED = 'bored'
    CALM = 'calm'
    CONFUSED = 'confused'
    CURIOUS = 'curious'
    DISAPPOINTED = 'disappointed'
    FRUSTRATED = 'frustrated'
    HAPPY = 'happy'
    INTERESTED = 'interested'
    OKAY = 'okay'
    SAD = 'sad'
    SURPRISED = 'surprised'

    AFFECTIVE_CHECK_OPTIONS = [
        (ANNOYED, 'Annoyed'),
        (BORED, 'Bored'),
        (CALM, 'Calm'),
        (CONFUSED, 'Confused'),
        (CURIOUS, 'Curious'),
        (DISAPPOINTED, 'Disappointed'),
        (FRUSTRATED, 'Frustrated'),
        (HAPPY, 'Happy'),
        (INTERESTED, 'Interested'),
        (OKAY, 'Okay'),
        (SAD, 'Sad'),
        (SURPRISED, 'Surprised')
    ]    

class ComprehensionCheck:
    scale_response_key = "scale_response"
    free_response_key = "free_response"

    class ComprehensionScale:
        NOTHING = 0
        LITTLE = 1
        LOT = 2

        COMPREHENSION_SCALE_CHOICES = [
            (NOTHING, 'Nothing'),
            (LITTLE, 'A little'),
            (LOT, 'A lot')
        ]

# Common abstract model characteristics of check responses
class CheckResponse(models.Model):
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.PROTECT)
    book = models.ForeignKey(to=Book, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# Comprehension check responses
class ComprehensionCheckResponse(CheckResponse):        
    comprehension_scale_response = models.IntegerField(        
        choices=ComprehensionCheck.ComprehensionScale.COMPREHENSION_SCALE_CHOICES,
        null=True
    )    
    comprehension_free_response = models.TextField(null=True)    

    def __str__(self):
        return '<CCResp %s/%d>' % (self.user.anon_id, self.book.id)


