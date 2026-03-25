from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from questions.models import Question
from quizzes.models import Quiz
from users.models import UserRole


# Create your views here.

class CreateQuestionView(LoginRequiredMixin,UserPassesTestMixin,CreateView):
    model = Question
    fields = ['question_type', 'question_text', 'general_feedback']
    template_name = 'create_question.html'

    def test_func(self):
        return self.request.user.role == UserRole.ADMIN or self.request.user.role == UserRole.TEACHER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = get_object_or_404(Quiz, id=self.kwargs.get('quiz_id'))
        return context

    def form_valid(self, form):
        form.instance.quiz_id = self.kwargs.get('quiz_id')
        return super().form_valid(form)


    def get_success_url(self):
        return reverse('create-questions', kwargs={'quiz_id': self.kwargs.get('quiz_id')})