from django.contrib.auth.models import User
from django.forms import ModelForm
from django import forms

class UserForm(ModelForm):
    password_change = forms.CharField(required=False, label='Password',
                               widget=forms.PasswordInput(attrs={
                                   'aria-label': 'Password',
                                   'placeholder': 'Leave unchanged',
                                   'autocomplete': 'new-password',
                                   'class': 'form-control',
                               }))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['username'].required = True

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'aria-label': 'First name', 'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'aria-label': 'Last name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'aria-label': 'Email', 'class': 'form-control'}),
            'username': forms.TextInput(attrs={'aria-label': 'Username', 'class': 'form-control'})
        }
