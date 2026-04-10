from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordResetForm, SetPasswordForm, \
    PasswordChangeForm
from django.contrib.auth import get_user_model

from users.models import Arrangement


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
    password1 = forms.CharField(label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        })
    )
    password2 = forms.CharField(label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        })
    )
    first_name = forms.CharField(label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    last_name = forms.CharField(label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    email = forms.EmailField(label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        })
    )
    role = forms.ChoiceField(label='Role', widget=forms.Select(attrs={
        'class': 'form-select',
        'id': 'role'
    }),
        choices=[
            (0,'Student'),
            (1,'Teacher'),
            (2,'Admin')
        ]
    )

    user_pic = forms.ImageField(label='Profile Picture',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'user_pic')

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


class UserUpdateForm(forms.ModelForm):
    extra_time_percentage = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        label='Extra Time',
    )

    rest_breaks = forms.BooleanField(
        required=False,
        label="Requires Rest Breaks"
    )

    special_equipment = forms.CharField(
        required=False,
        label='Special Equipment',
    )

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'username', 'role', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and hasattr(self.instance, 'arrangement') and self.instance.arrangement:
            self.fields['extra_time_percentage'].initial = self.instance.arrangement.extra_time
            self.fields['rest_breaks'].initial = self.instance.arrangement.rest_breaks
            self.fields['special_equipment'].initial = self.instance.arrangement.special_equipment

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        user = super().save(commit=commit)

        extra_time_inp = self.cleaned_data.get('extra_time_percentage')
        rest_breaks_inp = self.cleaned_data.get('rest_breaks')
        special_equip_inp = self.cleaned_data.get('special_equipment')

        if commit:
            needs_arrangement = bool(extra_time_inp  or rest_breaks_inp or special_equip_inp)

            if needs_arrangement:
                if hasattr(user, 'arrangement') and user.arrangement:
                    # Update existing
                    user.arrangement.extra_time = extra_time_inp or 0
                    user.arrangement.rest_breaks = rest_breaks_inp
                    user.arrangement.special_equipment = special_equip_inp
                    user.arrangement.save()
                else:
                    # Create ONE brand new arrangement with both values
                    new_arrangement = Arrangement.objects.create(
                        extra_time=extra_time_inp or 0,
                        rest_breaks=rest_breaks_inp,
                        special_equipment=special_equip_inp or ''
                    )
                    user.arrangement = new_arrangement
                    user.save(update_fields=['arrangement'])
            else:
                if hasattr(user, 'arrangement') and user.arrangement:
                    user.arrangement.delete()
        return user