from django import forms
from django.forms import Textarea


class TextInputForm(forms.Form):
    text = forms.fields.CharField(label='Text to analyze', widget=Textarea)


class TextSimplificationForm(forms.Form):
    text = forms.fields.CharField(label='Text to simplify', widget=Textarea)
    percent = forms.fields.IntegerField(label='How many words to change (percentage)',
                                        initial=10, min_value=0, max_value=100)
