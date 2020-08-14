from django import forms
from django.forms import Textarea


class TextInputForm(forms.Form):
    text = forms.fields.CharField(label='Text to analyze', widget=Textarea)
