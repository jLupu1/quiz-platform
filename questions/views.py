from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
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


@login_required(login_url='/users/login/')
def get_question_partial(request):
    question_type = request.GET.get('question_type')
    print(question_type)
    if question_type == 'mcq':
        return render(request,'partials/mcq_partial.html')
    elif question_type == 'either_or':
        return render(request,'partials/either_or_partial.html')
    elif question_type == 'short_answer':
        return render(request,"partials/short_answer_partial.html")
    elif question_type == 'essay':
        return render(request,'partials/essay_partial.html')
    elif question_type == 'text_filler':
        return render(request,'partials/text_filler_partial.html')
    else:
        return HttpResponse("")
@login_required(login_url='/users/login/')
def add_mcq_options(request):
    return render(request, "partials/mcq_single_option.html")

def get_either_or_partial(request):
    return render(request, "partials/either_or_partial.html")