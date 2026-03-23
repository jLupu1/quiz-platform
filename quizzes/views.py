from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect
from django.views.generic import CreateView

from quizzes.forms import CreateQuizForm
from quizzes.models import Quiz


# Create your views here.
class CreateQuiz(LoginRequiredMixin,UserPassesTestMixin,CreateView):
    model = Quiz
    template_name = 'create_quiz.html'
    form_class = CreateQuizForm

    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_teacher
