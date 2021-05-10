from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.forms import ModelForm, Form
from multiselectfield import MultiSelectFormField

from roster.models import Period, Roles, ClusiveUser, EducationLevels

class ClusiveLoginForm(AuthenticationForm):

    def confirm_login_allowed(self, user: User):
        super().confirm_login_allowed(user)
        if user.is_staff:
            return
        try:
            clusive_user = ClusiveUser.objects.get(user=user)
            if clusive_user.unconfirmed_email:
                raise forms.ValidationError('You need to validate your email address before you can log in',
                                            code='email_validate')
        except ClusiveUser.DoesNotExist:
            raise forms.ValidationError("Not a ClusiveUser", code='invalid')


class UserForm(ModelForm):
    # password field added by subclasses

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
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
        fields = ['first_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'aria-label': 'Display name/nickname', 'class': 'form-control'}),
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


# Used for simple cases where entering the password twice is not required.
class SimpleUserCreateForm(UserForm):
    password = forms.CharField(required=False, label='Password',
                               widget=forms.PasswordInput(attrs={
                                   'aria-label': 'Password',
                                   'autocomplete': 'new-password',
                                   'class': 'form-control',
                               }))


# For registration we use the standard Django behavior with double password inputs
class UserRegistrationForm(UserCreationForm):
    password1 = forms.CharField(
        label = '*Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'aria-label': 'Password', 'autocomplete': 'new-password', 'class': 'form-control'})
    )

    password2 = forms.CharField(
        label='*Password confirmation',
        strip=False,
        widget=forms.PasswordInput(attrs={'aria-label': 'Password', 'autocomplete': 'new-password', 'class': 'form-control'})
    )

    terms = forms.BooleanField(
        label='*Accept terms of use and privacy policy',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    education_levels = MultiSelectFormField(
        choices=EducationLevels.CHOICES,
        label='Education level of student(s) (select all that apply)',
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = '*Display name'
        self.fields['email'].label = '*Email'
        self.fields['email'].required = True
        self.fields['username'].label = '*Username'
        self.fields['username'].required = True
        #  Potential SSO user already logged in
        self.user = kwargs['initial'].get('user', None)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name # Display name
            self.fields['email'].initial = self.user.email
            self.fields['email'].disabled = True
            self.fields['username'].label = 'Username'
            self.fields['username'].required = False
            self.fields['username'].initial = self.user.username
            self.fields['password1'].required = False
            self.fields['password2'].required = False

    def clean(self):
        email = self.cleaned_data.get('email')
        user_with_that_email = User.objects.filter(email=email)
        if not self.is_logged_in(user_with_that_email):
            if user_with_that_email.exists():
                self.add_error('email', 'There is already a user with that email address.')
        return super().clean()

    def clean_username(self):
        username = self.cleaned_data.get('username')
        user_with_that_username = User.objects.filter(username=username)
        if not self.is_logged_in(user_with_that_username):
            if user_with_that_username.exists():
                self.add_error('username', 'There is already a user with that username')
        return username

    def _post_clean(self):
        if not self.cleaned_data.get('first_name'):
            self.cleaned_data['first_name'] = self.cleaned_data.get('username')
        super()._post_clean()

    def is_logged_in(self, criteria):
        if self.user:
            return (self.user in criteria)
        else:
            return False

    class Meta:
        model = User
        fields = ['first_name', 'password1', 'password2', 'email', 'username', 'education_levels']
        widgets = {
            'first_name': forms.TextInput(attrs={'aria-label': 'Display name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'aria-label': 'Email', 'class': 'form-control'}),
            'username': forms.TextInput(attrs={'aria-label': 'Username', 'class': 'form-control'}),
        }


class AccountRoleForm(Form):
    role = forms.ChoiceField(
        choices=[(Roles.TEACHER, "I'm a teacher"),
                 (Roles.PARENT, "I'm a parent"),
                 (Roles.STUDENT, "I'm a learner")],
        required=True,
        widget=forms.RadioSelect)


class AgeCheckForm(Form):
    of_age = forms.ChoiceField(
        choices=[(True, 'Yes'),
                 (False, 'No')],
        required=True,
        widget=forms.RadioSelect)


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
