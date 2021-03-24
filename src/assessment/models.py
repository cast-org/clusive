import logging

from django.db import models

from uuid import uuid4

from roster.models import ClusiveUser
from library.models import BookVersion

logger = logging.getLogger(__name__)

class ComprehensionCheck:
    scale_title = "How much did you learn from this reading?"
    free_response_title = "What's one thing you learned?"    

    class ComprehensionScale:
        NOTHING = 0
        LITTLE = 1
        LOT = 2

        COMPREHENSION_SCALE_CHOICES = [
            (NOTHING, 'Nothing'),
            (LITTLE, 'A little'),
            (LOT, 'A lot')
        ]

# Generic comprehension check responses
class ComprehensionCheckResponse(models.Model):
    id = models.CharField(primary_key=True, default=uuid4, max_length=36)    
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.PROTECT)
    book_version = models.ForeignKey(to=BookVersion, on_delete=models.PROTECT)       
    comprehension_scale_response = models.IntegerField(        
        choices=ComprehensionCheck.ComprehensionScale.COMPREHENSION_SCALE_CHOICES,
        default=ComprehensionCheck.ComprehensionScale.NOTHING
    )    
    comprehension_free_response = models.TextField(default="")
     

