from django.db import models

from roster.models import ClusiveUser


class WordModel(models.Model):
    """Stores the system's model of a particular user's relationship with a particular word."""
    # How strongly should these events be counted in our estimate of user interest in a word?
    FREE_LOOKUP_WEIGHT = 6
    CUED_LOOKUP_WEIGHT = 3
    RATING_WEIGHT = 2
    CUE_WEIGHT = -1

    KNOWLEDGE_RATINGS = {
        0: 'Never heard it',
        1: 'Heard it',
        2: 'Know it',
        3: 'Use it'
    }

    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE)
    word = models.CharField(max_length=256)
    rating = models.SmallIntegerField(null=True)
    interest = models.SmallIntegerField(default=0)
    cued_lookups = models.SmallIntegerField(default=0)
    free_lookups = models.SmallIntegerField(default=0)
    cued = models.SmallIntegerField(default=0)

    def knowledge_est(self):
        if self.rating!=None:
            return self.rating
        if self.cued_lookups>0 or self.free_lookups>0:
            return 1
        return None

    def knowledge_est_in_words(self):
        return self.KNOWLEDGE_RATINGS.get(self.knowledge_est())

    def interest_est(self):
        return self.interest

    # "Register" methods for various events that can effect ratings and interest

    def register_rating(self, rating):
        self.rating = rating
        self.interest += self.RATING_WEIGHT
        self.save()

    def register_wordbank_remove(self):
        self.interest = 0
        self.save()

    def register_cued_lookup(self):
        self.cued_lookups += 1
        self.interest += self.CUED_LOOKUP_WEIGHT
        self.save()

    def register_free_lookup(self):
        self.free_lookups += 1
        self.interest += self.FREE_LOOKUP_WEIGHT
        self.save()

    @classmethod
    def register_cue(cls, user, word):
        """Add one to the 'cued' statistic for a single word and user"""
        wm, created = WordModel.objects.get_or_create(user=user, word=word)
        wm.cued += 1
        if wm.interest>0:
            wm.interest += cls.CUE_WEIGHT
        wm.save()
        return wm

    @classmethod
    def register_cues(cls, user, words):
        """Add one to the 'cued' statistic for each of the words for the given user"""
        for word in words:
            cls.register_cue(user, word)

    @classmethod
    def is_valid_rating(cls, number):
        return isinstance(number, int) and number>=0 and number<=3

