from django import forms
from django.contrib.auth import get_user_model

from users.models import UserRole
from .models import Course
# It is best practice to use get_user_model() instead of importing CustomUser directly!
User = get_user_model()


class CourseCreationForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'teachers', 'students']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Intro to Java'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. COM1003'}),
            'teachers': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'students': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    # 1. Create two UI fields that ONLY exist on this form, not in the database
    teachers = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=UserRole.TEACHER),
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        required=False,
        label="Assign Teachers"
    )

    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=UserRole.STUDENT),
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        required=False,
        label="Enroll Students"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply Bootstrap to the string fields
        self.fields['name'].widget.attrs['class'] = 'form-control'
        self.fields['code'].widget.attrs['class'] = 'form-control'

        # Optional pro-tip: If you ever reuse this form to EDIT a course later,
        # this will pre-fill the dropdowns with the currently enrolled people!
        if self.instance and self.instance.pk:
            self.fields['teachers'].initial = self.instance.enrollment.filter(role=UserRole.TEACHER)
            self.fields['students'].initial = self.instance.enrollment.filter(role=UserRole.STUDENT)

    # 3. MASH THEM TOGETHER ON SAVE
    def save(self, commit=True):
        # Save the basic text fields (name, code) first to get a database ID
        course = super().save(commit=False)

        if commit:
            course.save()  # Must save first before we can add ManyToMany relationships

            # Grab the lists from our two UI boxes
            selected_teachers = self.cleaned_data.get('teachers', [])
            selected_students = self.cleaned_data.get('students', [])

            # Combine them into one master list
            all_enrolled_users = list(selected_teachers) + list(selected_students)

            # Dump the master list into the actual database field using .set()
            course.enrollment.set(all_enrolled_users)

        return course