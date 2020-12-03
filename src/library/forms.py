import logging

from django import forms

from library.models import Book
from roster.models import Period, ClusiveUser

logger = logging.getLogger(__name__)


class UploadForm(forms.Form):
    file = forms.FileField(label='File')


class MetadataForm(forms.ModelForm):
    cover = forms.FileField(required=False, label='Choose new image...')
    cover.widget.attrs.update({'accept': 'image/*'})

    use_orig_cover = forms.BooleanField(label='Use this', required=False, initial=False)
    use_orig_cover.widget.attrs.update({'class': 'usethis-cover'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ''

    class Meta:
        model = Book
        fields = ['title', 'author', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Content title'}),
            'author': forms.TextInput(attrs={'placeholder': 'Author of the content'}),
            'description': forms.Textarea(attrs={'placeholder': 'Provide a brief description to show on the Library page.'}),
        }


class PeriodModelMultipleChoiceField(forms.ModelMultipleChoiceField):

    def label_from_instance(self, period):
        return period.name


class ShareForm(forms.Form):
    periods = PeriodModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        queryset=Period.objects.all(),
        required=False)

    def __init__(self, *args, **kwargs):
        clusive_user : ClusiveUser
        clusive_user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        periods = clusive_user.periods.all()
        self.fields['periods'].queryset = periods

