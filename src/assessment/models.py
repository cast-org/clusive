import logging

from django.db import models
from django.db.models import Count
from django.utils import timezone

from django.core import serializers

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
    scale_response_key = "scaleResponse"
    free_response_key = "freeResponse"

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

# Affective check responses
class AffectiveCheckResponse(CheckResponse):
    annoyed_option_response = models.BooleanField(null=False, default=False)
    bored_option_response = models.BooleanField(null=False, default=False)
    calm_option_response = models.BooleanField(null=False, default=False)
    confused_option_response = models.BooleanField(null=False, default=False)
    curious_option_response = models.BooleanField(null=False, default=False)
    disappointed_option_response = models.BooleanField(null=False, default=False)
    frustrated_option_response = models.BooleanField(null=False, default=False)
    happy_option_response = models.BooleanField(null=False, default=False)
    interested_option_response = models.BooleanField(null=False, default=False)
    okay_option_response = models.BooleanField(null=False, default=False)
    sad_option_response = models.BooleanField(null=False, default=False)
    surprised_option_response = models.BooleanField(null=False, default=False)

    # Returns all True options as a single comma-separated string
    # Used for Caliper event creation
    def toAnswerString(self):
        model_values = self.__dict__
        answer_string = ""
        for val in model_values:
            if "option_response" in val and model_values[val]:
                if(len(answer_string) == 0):
                    answer_string = val.split("_")[0]
                else:
                    answer_string = answer_string + "," + val.split("_")[0]
        return answer_string

    def __str__(self):
        return '<ACResp %s/%d>' % (self.user.anon_id, self.book.id)


class StarRatingScale:
    ONE_STAR = 1
    TWO_STAR = 2
    THREE_STAR = 3
    FOUR_STAR = 4

    STAR_CHOICES = [
        (ONE_STAR, 'Really don\'t like it'),
        (TWO_STAR, 'Don\'t like it'),
        (THREE_STAR, 'Like it'),
        (FOUR_STAR, 'Really like it'),
    ]


class ClusiveRatingResponse(models.Model):
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE)
    star_rating = models.SmallIntegerField(choices=StarRatingScale.STAR_CHOICES)
    created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_results(cls):
        return cls.objects\
            .values('star_rating')\
            .annotate(count=Count('star_rating'))

    @classmethod
    def get_graphable_results(cls):
        """Return results in a graphable form"""
        results = cls.get_results()
        total = sum(r['count'] for r in results)
        maximum = max(r['count'] for r in results)
        max_percent = round(100*maximum/total)
        # Set up data structure
        data = {}
        for value, name in StarRatingScale.STAR_CHOICES:
            data[value] = {
                'value': value,
                'name': name
            }

        # Add percentage and maximum
        for r in results:
            item = data[r['star_rating']]
            item['percent'] = round(100*r['count']/total)
            item['max'] = max_percent
        # Unpack map to sorted list.
        result = list(data.values())
        result.sort(key=lambda item: item['value'])
        logger.debug('Data for graph: %s', result)
        return result

    def __str__(self):
        return '<ClusiveRatingResp %s:%d>' % (self.user.anon_id, self.star_rating)
