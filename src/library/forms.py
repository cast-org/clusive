import logging

from django import forms

from library.models import Book

logger = logging.getLogger(__name__)


class UploadForm(forms.Form):
    file = forms.FileField(label='File')


# class MetadataForm(forms.Form):
#     title = forms.CharField(label='Title', max_length=256, required=True)
#     author = forms.CharField(label='Author', max_length=256)
#     description = forms.CharField(label='Description')

class MetadataForm(forms.ModelForm):
    # Extra field
    cover = forms.FileField(required=False, label='Choose new image...')
    cover.widget.attrs.update({'accept': 'image/*'})

    class Meta:
        model = Book
        fields = ['title', 'author', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Title of the content item'}),
            'author': forms.TextInput(attrs={'placeholder': 'Author of the content item'}),
            'description': forms.Textarea(attrs={'placeholder': 'Brief description to show on the library page.'}),
        }