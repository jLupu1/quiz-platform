from cProfile import label

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordResetForm, SetPasswordForm, \
    PasswordChangeForm
from django.contrib.auth import get_user_model


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your username',
        'id': 'username',
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )

class CustomSignupForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
    }))
    password1 = forms.CharField(label='Password *',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        })
    )
    password2 = forms.CharField(label='Confirm Password *',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        })
    )
    first_name = forms.CharField(label='First Name *',
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    last_name = forms.CharField(label='Last Name *',
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    email = forms.EmailField(label='Email *',
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        })
    )
    role = forms.ChoiceField(label='Role *', widget=forms.Select(attrs={
        'class': 'form-select',
        'id': 'role'
    }),
        choices=[
            (0,'Student'),
            (1,'Teacher'),
            (2,'Admin')
        ]
    )

    user_picture = forms.ImageField(label='Profile Picture',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'user_picture')

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
        })
    )

class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Loop through Django's default fields and add Bootstrap styling
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        # Optional: Rename the labels to look a bit cleaner
        self.fields['new_password1'].label = "New Password"
        self.fields['new_password2'].label = "Confirm Password"

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

