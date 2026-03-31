from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, UpdateView

from courses.models import Course
from quizzes.forms import CreateQuizForm
from quizzes.models import Quiz, QuizQuestion


# Create your views here.
class CreateQuiz(LoginRequiredMixin,UserPassesTestMixin,CreateView):
    model = Quiz
    template_name = 'create_quiz.html'
    form_class = CreateQuizForm
    success_url = 'create_questions'

    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_teacher
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        course = get_object_or_404(Course, id=self.kwargs['course_id'])

        context['course'] = course
        return context

    def form_valid(self, form):
        form.instance.course_id = self.kwargs.get('course_id')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('create_question', kwargs={'quiz_id': self.object.id})

class EditQuiz(LoginRequiredMixin,UserPassesTestMixin,UpdateView):
    model = Quiz
    template_name = 'edit_quiz.html'
    fields = [
        'name', 'introduction', 'open_date', 'close_date',
        'time_limit', 'maximum_attempts', 'maximum_marks'
    ]


    def test_func(self, **kwargs):
        quiz = get_object_or_404(Quiz, id=self.kwargs['pk'])
        course = get_object_or_404(Course, id=quiz.course_id)
        is_enrolled = course.enrollment.filter(id=course.id).exists()

        return self.request.user.is_staff_member or is_enrolled


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questions'] = QuizQuestion.objects.filter(quiz=self.object)
        return context

    def get_success_url(self):
        return reverse('edit-quiz', kwargs={'pk': self.object.pk})