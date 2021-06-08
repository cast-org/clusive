from django.forms import ModelForm

from assessment.models import ClusiveRatingResponse


class ClusiveRatingForm(ModelForm):

    class Meta:
        model = ClusiveRatingResponse
        fields = ['star_rating']
