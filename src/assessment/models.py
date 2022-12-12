from datetime import timedelta
import logging
import math

from django.db import models
from django.db.models import Count, Sum
from django.utils import timezone

from library.models import Book
from roster.models import ClusiveUser, ResearchPermissions, Roles

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
    custom_response_key = "customResponse"

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
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ComprehensionCheckResponse(CheckResponse):
    """
    Latest response of a student to the comprehension-related questions on a Book.
    Includes the multiple-choice response, free text, as well as the response to any custom question
    their teacher may have asked.
    """
    comprehension_scale_response = models.IntegerField(
        choices=ComprehensionCheck.ComprehensionScale.COMPREHENSION_SCALE_CHOICES,
        null=True, blank=True
    )
    comprehension_free_response = models.TextField(null=True, blank=True)
    custom_response = models.TextField(null=True, blank=True)

    def get_answer(self):
        for choice in ComprehensionCheck.ComprehensionScale.COMPREHENSION_SCALE_CHOICES:
            if choice[0] == self.comprehension_scale_response:
                return choice[1]
        return None

    @classmethod
    def get_counts(cls, book, period):
        """
        Get comprehension check stats for the given book and period.
        :return: a structure like this:
        { 'max':  <maximum of any of the counts>,
          'items': [
            { 'label': 'Nothing', 'value': 1 }
            { 'label': 'A little', 'value': 7 },
            { 'label': 'A lot', 'value': 4 }
          ]
        }
        """
        comp_check_counts = list(cls.objects \
            .filter(book=book, user__periods=period, user__role=Roles.STUDENT) \
            .values('comprehension_scale_response').annotate(count=Count('id')))
        max = 0
        data = []
        for option in ComprehensionCheck.ComprehensionScale.COMPREHENSION_SCALE_CHOICES:
            count_item = [c['count'] for c in comp_check_counts if c['comprehension_scale_response'] == option[0]]
            count = count_item[0] if count_item else 0
            data.append({
                'label': option[1],
                'value': count,
            })
            if count > max:
                max = count
        return { 'max': max,
                 'items': data }

    @classmethod
    def get_class_details_custom_responses(cls, book, period):
        """
        Get comp check responses that include a custom-question answer for the given book and period, as a simple list.
        :param book:
        :param period:
        :return: list of responses in student name order.
        """
        responses = cls.objects.filter(book=book, user__periods=period, user__role=Roles.STUDENT,
                                       custom_response__isnull=False) \
            .order_by('user__user__first_name')
        return responses

    @classmethod
    def get_class_details_by_scale(cls, book, period):
        """
        Get comp check responses for the given book and period, categorized by scale response.
        :param book:
        :param period:
        :return: list of lists with the related information.
        """
        responses = cls.objects.filter(book=book, user__periods=period, user__role=Roles.STUDENT)\
            .order_by('user__user__first_name')
        details = []
        for option in ComprehensionCheck.ComprehensionScale.COMPREHENSION_SCALE_CHOICES:
            details.append({
                'label': option[1],
                'items': [c for c in responses if c.comprehension_scale_response == option[0]]
            })
        return details

    def __str__(self):
        return '<CCResp %s/%d>' % (self.user.anon_id, self.book.id)


affect_words = ['surprised', 'interested', 'happy', 'curious', 'calm', 'okay',
                'bored', 'sad', 'disappointed', 'confused', 'frustrated', 'annoyed', ]

class AffectiveCheckResponse(CheckResponse):
    """
    Single user response to affect check prompt.
    """
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

    affect_free_response = models.TextField(null=True)

    def get_by_name(self, name):
        return getattr(self, name + '_option_response')

    # Returns the values as a list in affect_words defined order
    def to_list(self):
        result = []
        for word in affect_words:
            result.append(self.get_by_name(word))
        return result

    # Returns all True words as a list
    def to_answer_list(self):
        answers = []
        for word in affect_words:
            if self.get_by_name(word):
                answers.append(word)
        return answers

    # Returns all True options as a single comma-separated string
    # Used for Caliper event creation
    def to_answer_string(self):
        return ','.join(self.to_answer_list())

    def __str__(self):
        return '<ACResp %s/%d>' % (self.user.anon_id, self.book.id)

    @classmethod
    def recent_with_word(cls, user: ClusiveUser, word, time_scale=0):
        """
        Construct QuerySet for the most-recent responses by a user that include
        a true value for the given affect word.  If `time_scale` is provided and
        non-zero, it is the most recent number of days (zero means "all time").
        """
        field = word + '_option_response'
        filters = { 'user': user,
                   field: True }
        if time_scale != 0:
            filters['updated__gte'] = timezone.now() - timedelta(days=time_scale)
        return cls.objects.filter(**filters).order_by('-updated')


class AffectiveSummary(models.Model):
    annoyed      = models.IntegerField(default=0)
    bored        = models.IntegerField(default=0)
    calm         = models.IntegerField(default=0)
    confused     = models.IntegerField(default=0)
    curious      = models.IntegerField(default=0)
    disappointed = models.IntegerField(default=0)
    frustrated   = models.IntegerField(default=0)
    happy        = models.IntegerField(default=0)
    interested   = models.IntegerField(default=0)
    okay         = models.IntegerField(default=0)
    sad          = models.IntegerField(default=0)
    surprised    = models.IntegerField(default=0)

    class Meta:
        abstract = True

    def update(self, old_values, new_values):
        """
        Update the totals for a new response, or a changed response.
        :param old_values: list representation of previous responses to be subtracted out, or None.
        :param new_response: list representation of new response to be added in.
        :return: self
        """
        for (i, word) in enumerate(affect_words):
            old_val = old_values[i] if old_values else False
            new_val = new_values[i]
            if old_val != new_val:
                delta = 1 if new_val else -1
                setattr(self, word, getattr(self, word) + delta)
        return self

    # Return a simple list of the values for each word
    def to_list(self):
        return [getattr(self, word) for word in affect_words]

    def to_map(self):
        return {word: getattr(self, word) for word in affect_words}

    def maximum_value(self):
        return max(self.to_list())

    # Calculate the values to show in the starburst visualization for each word
    def scaled_values(self):
        """
        Calculate the values to show in the starburst visualization.
        :return: data structure for in a format convenient for sending to the visualization: [ { 'word': value }, ... ]
        """
        # testvals = [1,  2,  3,  4,  5, 10,
        #             20, 30, 40, 50, 75, 100]
        # maximum = max(testvals)
        # return [{ 'word': w, 'value': AffectiveSummary.scale_value(testvals[i], maximum) } for i, w in enumerate(affect_words)]
        maximum = self.maximum_value()
        map = self.to_map()
        return [{ 'word': w, 'value': AffectiveSummary.scale_value(map[w], maximum) } for w in affect_words]

    @classmethod
    def scale_values(cls, instance):
        """
        Convert instance to visualization data structure with null safety.
        Call scaled_values on the instance if one is provided.
        If the argument is None, then return the same data structure but with all 0 values.
        :param summary: an AffectiveSummary, or None
        :return: data structure for visualization: [ { 'word': value }, ... ]
        """
        if instance:
            return instance.scaled_values()
        else:
            return [{ 'word':w, 'value': 0} for w in affect_words]

    @classmethod
    def aggregate_and_scale(cls, query_set):
        """Given a QuerySet that would return multiple AffectiveSummarys,
        this asks the database to sum them all and then returns them scaled and ready for visualization."""
        sum_commands = [Sum(w) for w in affect_words]
        summed = query_set.aggregate(*sum_commands)
        maximum = max([summed[w+'__sum'] or 0 for w in affect_words])
        return [{ 'word': w, 'value': cls.scale_value(summed[w+'__sum'], maximum) } for w in affect_words]

    @classmethod
    def scale_value(cls, value, maximum):
        # Transform absolute value to scaled value relative to the given maximum.
        # Output of this formula needs be 0-100.
        # Uses a square-root transformation to compress the range because this is returning a radius
        # but the visualization fills in an area - area is proportional to r^2.
        if value and maximum:
            return min(100, round(100 * math.sqrt(value/maximum)))
        else:
            return 0

    @classmethod
    def most_with_word(cls, word):
        """Construct QuerySet for the summaries with the highest total for the given affect word."""
        # At least 1 vote, order by number of votes desc.
        filters = { word + '__gte': 1 }
        return cls.objects.filter(**filters).order_by('-'+word)


class AffectiveUserTotal(AffectiveSummary):
    user         = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)

    def __str__(self):
        return '<AffUserTotal: %s>' % self.user


class AffectiveBookTotal(AffectiveSummary):
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE, db_index=True)

    def __str__(self):
        return '<AffBookTotal: %s>' % self.book


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
        """Count all ratings except those from test accounts, return count of votes for each rating."""
        return cls.objects\
            .exclude(user__permission=ResearchPermissions.TEST_ACCOUNT)\
            .values('star_rating')\
            .annotate(count=Count('star_rating'))

    @classmethod
    def get_graphable_results(cls):
        """Return results in a graphable form"""
        results = cls.get_results()
        total = sum(r['count'] for r in results)
        if total < 10:
            logger.debug('Not enough votes to display graph (%d)', total)
            return []
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
