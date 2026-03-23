from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView

from courses.models import Course
from quizzes.forms import CreateQuizForm
from quizzes.models import Quiz


# Create your views here.
class CreateQuiz(LoginRequiredMixin,UserPassesTestMixin,CreateView):
    model = Quiz
    template_name = 'create_quiz.html'
    form_class = CreateQuizForm

    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_teacher
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        course = get_object_or_404(Course, id=self.kwargs['course_id'])

        context['course'] = course
        return context
        
