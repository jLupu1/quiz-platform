from django import forms

from courses.models import Course
from quizzes.models import Quiz


class CreateQuizForm(forms.ModelForm):
    class Meta:
        model = Quiz

        fields = ['name', 'introduction', 'open_date', 'close_date', 'time_limit',
                  'maximum_attempts', 'delay_between_attempts', 'shuffle_questions', 'shuffle_answers',
                  'review_attempt', 'review_right_answer', 'review_marks', 'review_specific_feedback',
                  'review_general_feedback', 'review_overall_feedback', 'show_user_picture', 'anonymise_student',
                  'anonymise_marker', 'overall_feedback','password']

        widgets = {
            'open_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'close_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'