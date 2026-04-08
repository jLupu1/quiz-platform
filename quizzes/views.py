from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import CreateView, UpdateView, TemplateView

from courses.models import Course
from questions.models import McqOption, EitherOrOption, QuestionType
from quizzes.forms import CreateQuizForm
from quizzes.models import Quiz, QuizQuestion, Attempt, Response, ResponseOption


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

    def form_invalid(self, form):
        if 'close_date' in form.errors:
            messages.error(self.request, form.errors['close_date'][0])
        else:
            messages.error(self.request, "Please correct the errors in the form below.")

        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('create_question', kwargs={'quiz_id': self.object.id})

class EditQuiz(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Quiz
    template_name = 'manage/edit_quiz.html'

    # It is usually safer to define these in a forms.py file, but this works perfectly!
    fields = [
        'name', 'introduction', 'overall_feedback', 'open_date', 'close_date', 'status',
        'time_limit', 'maximum_attempts', 'maximum_marks', 'delay_between_attempts',
        'shuffle_questions', 'shuffle_answers', 'review_attempt',
        'review_right_answer', 'review_marks', 'review_specific_feedback',
        'review_general_feedback', 'review_overall_feedback', 'show_user_picture',
        'anonymise_student', 'anonymise_marker'
    ]

    def test_func(self):
        return is_staff_and_enrolled(self.request, self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Using .prefetch_related or just querying the reverse relationship
        context['questions'] = self.object.quizquestion_set.all()
        return context

    def form_valid(self, form):
        messages.success(self.request, "Quiz settings updated successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        # Check if our custom rule for the 'status' field was triggered
        if 'status' in form.errors:
            messages.error(self.request, form.errors['status'][0])
        elif 'close_date' in form.errors:
            messages.error(self.request, form.errors['close_date'][0])
        else:
            messages.error(self.request, "Please correct the errors in the form below.")

        return super().form_invalid(form)

    def get_success_url(self):
        # Make sure 'edit_quiz' matches exactly what is in your urls.py!
        return reverse('edit-quiz', kwargs={'pk': self.object.pk})

@login_required(login_url='/users/login/')
@require_http_methods(["DELETE"]) # Block GET links
def delete_quiz(request, **kwargs):
    quiz_id = kwargs['pk']
    if not is_staff_and_enrolled(request,quiz_id):
        raise PermissionDenied("You are not enrolled in this module/course or not a staff member")

    quiz = get_object_or_404(Quiz, pk=kwargs['pk'])
    quiz.delete()

    return HttpResponse("")


class StudentTakeQuiz(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "student/student_quiz_view.html"

    def test_func(self):
        attempt_id = self.kwargs.get('attempt_id')
        attempt = get_object_or_404(Attempt, id=attempt_id)

        return is_student_enrolled(self.request, attempt.quiz.id)

    def get(self, request, *args, **kwargs):
        attempt = get_object_or_404(Attempt, id=self.kwargs['attempt_id'], user=self.request.user)

        if not attempt.quiz.is_currently_available:
            messages.error(request, "This quiz has been closed.")
            return redirect('course_detail', course_id=attempt.quiz.course_id)

        if attempt.is_completed or attempt.is_time_up:
            return redirect('quiz_landing', quiz_id=attempt.quiz.id)

        context = self.get_context_data(**kwargs)
        context['attempt'] = attempt
        context['deadline_time'] = attempt.deadline.isoformat()
        context['start_time'] = attempt.start_time.isoformat()

         # TODO shuffle the list ...
        context['question_list'] = attempt.quiz.quizquestion_set.all().order_by('order_sequence')
        context['first_question'] = context['question_list'].first()

        answered_ids = attempt.responses.values_list('quiz_question_id', flat=True)
        context['answered_question_ids'] = list(answered_ids)

        return self.render_to_response(context)

# TODO restrictions
def quiz_landing_page(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)

    if not quiz.is_currently_available:
        messages.error(request, "This quiz is not currently open for attempts.")
        return redirect('course_detail',pk=quiz.course_id)

    past_attempts = Attempt.objects.filter(quiz=quiz).order_by('-start_time')
    attempt_count = past_attempts.count()

    latest_attempt = past_attempts.first()
    if latest_attempt and not latest_attempt.is_time_up and not latest_attempt.is_completed:
#         resume the attempt
        return redirect('take_quiz', attempt_id=latest_attempt.id)

    # if start new attempt clicked
    if request.method == "POST":
        # -1 attempt mean unlimited
        if quiz.maximum_attempts != -1 and attempt_count >= quiz.maximum_attempts:
            #too many attempts
            messages.error(request, "You have used all of your attempts")
            return redirect('course_detail', course_id=quiz.course_id)

        # start new attempt
        new_attempt = Attempt.objects.create(
            quiz=quiz,
            user=request.user,
            attempt_count=attempt_count + 1,
        )
        return redirect('take_quiz', attempt_id=new_attempt.id)

    # This is the get to show the landing page
    context = {
        'quiz': quiz,
        'attempt_count': attempt_count,
        'attempts_left' : quiz.maximum_attempts - attempt_count if quiz.maximum_attempts != -1 else 'Unlimited',
    }
    return render(request, 'student/quiz_landing_page.html', context)

# TODO restrictions
def question_engine(request, attempt_id, question_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
    quiz_question = get_object_or_404(QuizQuestion, id=question_id, quiz=attempt.quiz)

    question_list = list(attempt.quiz.quizquestion_set.all().order_by('order_sequence'))
    #TODO shuffle the list ...
    current_question_number = question_list.index(quiz_question) + 1

    if attempt.is_time_up:
        return HttpResponseForbidden("Time is up! Answers can no longer be saved.")

    successfully_saved = False
    existing_response = None

    if request.method == "POST":
        response, created = Response.objects.get_or_create(
            attempt=attempt,
            quiz_question=quiz_question,
        )
        existing_response = response

        if 'answer_text' in request.POST:
            response.answer_given = request.POST.get('answer_text')
            response.save()
            successfully_saved = True

        elif 'mcq_answer' in request.POST:
            option_id_list = request.POST.getlist('mcq_answer')
            response.selected_options.all().delete()
            for option_id in option_id_list:
                ResponseOption.objects.create(response=response, mcq_option_id=option_id)
            successfully_saved = True

        elif 'eo_answer' in request.POST:
            option_id = request.POST.get('eo_answer')
            response.selected_options.all().delete()
            ResponseOption.objects.create(response=response, eo_option_id=option_id)
            successfully_saved = True

    elif request.method == "GET":
        existing_response = Response.objects.filter(attempt=attempt, quiz_question=quiz_question).first()

        # Extract all saved option IDs into a list
    existing_response_option_ids = []
    if existing_response:
        # MCQ
        existing_response_option_ids.extend(
            existing_response.selected_options.exclude(mcq_option_id__isnull=True).values_list('mcq_option_id',
                                                                                               flat=True)
        )
        # EO
        existing_response_option_ids.extend(
            existing_response.selected_options.exclude(eo_option_id__isnull=True).values_list('eo_option_id', flat=True)
        )

    context = {
        'attempt': attempt,
        'quiz_question': quiz_question,
        'successfully_saved': successfully_saved,
        'existing_response': existing_response,
        'existing_response_option_ids': existing_response_option_ids,
        'current_question_number': current_question_number,
    }

    # Assuming quiz_question.question.question_type exists (e.g., 'ESSAY', 'MCQ', 'TF')
    template_map = {
        QuestionType.ESSAY_QUESTION.name: 'partials/student_essay_partial.html',
        QuestionType.SHORT_ANSWER.name: 'partials/student_sa_partial.html',
        QuestionType.MCQ.name: 'partials/student_mcq_partial.html',
        QuestionType.EITHER_OR.name: 'partials/student_eo_partial.html'
    }

    # Convert the integer to the Enum, grab the name, and look it up!
    question_enum_name = QuestionType(quiz_question.question.question_type).name
    # TODO create a default blank or smth partial like a smth went wrong oops
    template_name = template_map.get(question_enum_name, 'partials/student_essay.html')
    return render(request, template_name, context)

# TODO Restrictions
@login_required
@require_POST  # Security: Forces this view to ONLY accept POST requests
def submit_quiz(request, attempt_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)

    # 1. Prevent double-submission
    if attempt.is_completed:
        messages.info(request, "This quiz attempt has already been submitted.")
        return redirect('quiz_results', attempt_id=attempt.id)

    # 2. Lock it down!
    attempt.is_completed = True
    attempt.save()
    attempt.grade_attempt()

    # 3. Send them to the results/celebration page
    messages.success(request, "Quiz submitted successfully!")
    return redirect('quiz_results', attempt_id=attempt.id)

# TODO Restrictions

@login_required
def quiz_results(request, attempt_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)

    if not attempt.is_completed:
        return redirect('take_quiz', attempt_id=attempt.id)

    total_questions = attempt.quiz.quizquestion_set.count()
    answered_questions = attempt.responses.count()

    # Sees if there is response with null - meaning essay TODO for now
    pending_grading = attempt.responses.filter(marks_given__isnull=True).exists()


    context = {
        'attempt': attempt,
        'total_questions': total_questions,
        'answered_questions': answered_questions,
        'unanswered_count': total_questions - answered_questions,
        'pending_grading':pending_grading,
        'review_marks':attempt.quiz.review_marks

    }

    return render(request, 'student/quiz_results.html', context)


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