from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, UpdateView, DetailView

from courses.models import Course
from quizzes.forms import CreateQuizForm
from quizzes.models import Quiz, QuizQuestion, Attempt


# Create your views here.
class CreateQuiz(LoginRequiredMixin,UserPassesTestMixin,CreateView):
    model = Quiz
    template_name = 'manage/create_quiz.html'
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
    template_name = 'manage/edit_quiz.html'
    fields = [
        'name', 'introduction', 'overall_feedback', 'open_date', 'close_date',
        'time_limit', 'maximum_attempts', 'maximum_marks', 'delay_between_attempts',
        'shuffle_questions', 'shuffle_answers', 'review_attempt',
        'review_right_answer', 'review_marks', 'review_specific_feedback',
        'review_general_feedback', 'review_overall_feedback', 'show_user_picture',
        'anonymise_student', 'anonymise_marker'
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

@login_required(login_url='/users/login/')
@require_http_methods(["DELETE"]) # Block GET links
def delete_quiz(request, **kwargs):
    quiz_id = kwargs['pk']
    if not is_staff_and_enrolled(request,quiz_id):
        raise PermissionDenied("You are not enrolled in this module/course")

    quiz = get_object_or_404(Quiz, pk=kwargs['pk'])
    quiz.delete()

    return HttpResponse("")


class StudentCompleteQuiz(LoginRequiredMixin,UserPassesTestMixin,DetailView):
    model = Quiz
    template_name = "student/student_quiz_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt,created = Attempt.objects.get_or_create(user=self.request.user, quiz=self.object)
        # HH:MM:SS
        context['deadline_time'] = attempt.deadline.isoformat()
        context['start_time'] = attempt.start_time.isoformat()
        context['question_list'] = QuizQuestion.objects.filter(quiz=self.object)

        return context

    def test_func(self):
        return is_student_enrolled(self.request,self.kwargs.get('pk') )

def is_staff_and_enrolled(request,quiz_id):
    if request.user.is_admin:
        return True
    is_enrolled = user_is_enrolled(request,quiz_id)
    return is_enrolled and request.user.is_staff_member

def is_student_enrolled(request,quiz_id):
    is_enrolled = user_is_enrolled(request,quiz_id)
    return is_enrolled and request.user.is_student

def user_is_enrolled(request,quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    course = get_object_or_404(Course, id=quiz.course_id)
    return course.enrollment.filter(id=request.user.id).exists()