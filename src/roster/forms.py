from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.forms import ModelForm
from django import forms

from roster.models import Period


class UserForm(ModelForm):
    # password field added by subclasses

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['username'].required = True

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data by super().
        password = self.cleaned_data.get('password')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password', error)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'aria-label': 'First name', 'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'aria-label': 'Last name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'aria-label': 'Email', 'class': 'form-control'}),
            'username': forms.TextInput(attrs={'aria-label': 'Username', 'class': 'form-control'})
        }


class UserEditForm(UserForm):
    password = forms.CharField(required=False, label='Password',
                               widget=forms.PasswordInput(attrs={
                                   'aria-label': 'Password',
                                   'placeholder': 'Leave unchanged',
                                   'autocomplete': 'new-password',
                                   'class': 'form-control',
                               }))


class UserCreateForm(UserForm):
    password = forms.CharField(required=False, label='Password',
                               widget=forms.PasswordInput(attrs={
                                   'aria-label': 'Password',
                                   'autocomplete': 'new-password',
                                   'class': 'form-control',
                               }))

class PeriodForm(ModelForm):

    class Meta:
        model = Period
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'aria-label': 'Class name',
                'class': 'form-control',
            })
        }
