from django.db import models

from roster.models import ClusiveUser


class WordModel(models.Model):
    """Stores the system's model of a particular user's relationship with a particular word."""
    # How strongly should these events be counted in our estimate of user interest in a word?
    FREE_LOOKUP_WEIGHT = 5
    CUED_LOOKUP_WEIGHT = 2
    CUE_WEIGHT = -1

    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE)
    word = models.CharField(max_length=256)
    rating = models.SmallIntegerField(null=True)
    cued_lookups = models.SmallIntegerField(default=0)
    free_lookups = models.SmallIntegerField(default=0)
    cued = models.SmallIntegerField(default=0)

    def knowledge_est(self):
        if self.rating!=None:
            return self.rating
        if self.cued_lookups>0 or self.free_lookups>0:
            return 1
        return None

    def interest_est(self):
        return self.free_lookups*self.FREE_LOOKUP_WEIGHT \
               + self.cued_lookups*self.CUED_LOOKUP_WEIGHT \
               + self.cued*self.CUE_WEIGHT

    @classmethod
    def register_cues(cls, user, words):
        """Add one to the 'cued' statistic for each of the words for the given user"""
        for word in words:
            wm, created = WordModel.objects.get_or_create(user=user, word=word)
            wm.cued += 1
            wm.save()

    @classmethod
    def is_valid_rating(cls, number):
        return isinstance(number, int) and number>=0 and number<=3

