from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, ListView, UpdateView
from courses.models import Course
from questions.models import Question, McqOption, ShortAnswerQuestionOption, EssayQuestionOption, EitherOrOption, \
    TextFiller, QuestionType
from quizzes.models import Quiz, QuizQuestion
from users.models import UserRole
from django.core.exceptions import PermissionDenied, ValidationError


# Create your views here.

class CreateQuestionView(LoginRequiredMixin,UserPassesTestMixin,CreateView):
    model = Question
    fields = ['question_type', 'question_text', 'general_feedback']
    template_name = 'create_question.html'

    def test_func(self):
        return is_staff_and_enrolled(self.request, self.kwargs['quiz_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = get_object_or_404(Quiz, id=self.kwargs.get('quiz_id'))
        context['added_questions'] = QuizQuestion.objects.filter(quiz=context['quiz'])

        return context

    def form_valid(self, form):
        question_type = self.request.POST.get('question_type')

        # (MCQ) Validation
        if question_type == '0':
            mcq_texts = self.request.POST.getlist('mcq_option_text')

            # at least two options
            if len(mcq_texts) < 2:
                form.add_error(None, 'Multiple Choice questions require at least two options.')
                return self.form_invalid(form)

            # any of the provided options empty or just spaces
            for text in mcq_texts:
                if not text or not text.strip():
                    form.add_error(None,
                                   'All Multiple Choice options must contain text. Blank options are not allowed.')
                    return self.form_invalid(form)

        # Either/Or Validation
        elif question_type == '1':
            eo_texts = self.request.POST.getlist('eo_label_text')

            # exactly two options
            if len(eo_texts) != 2:
                form.add_error(None, 'Either/Or questions must have exactly two options (e.g., True and False).')
                return self.form_invalid(form)

            # neither option can be blank
            for text in eo_texts:
                if not text or not text.strip():
                    form.add_error(None, 'Both Either/Or options must contain text. Blank labels are not allowed.')
                    return self.form_invalid(form)

        # Short Answer Validation
        elif question_type == '2':
            sa_answer = self.request.POST.get('sa_answer')
            if not sa_answer or not sa_answer.strip():
                form.add_error(None, 'You must provide an Acceptable / Model Answer for Short Answer questions.')
                return self.form_invalid(form)

        with transaction.atomic():
            question = form.save(commit=False)
            question.save()

            quiz = get_object_or_404(Quiz, id=self.kwargs.get('quiz_id'))
            general_feedback = self.request.POST.get('general_feedback')
            order_sequence = QuizQuestion.objects.filter(quiz=quiz).count() + 1
            QuizQuestion.objects.create(
                question=question,
                quiz=quiz,
                general_feedback=general_feedback,
                order_sequence=order_sequence,
            )

            # MCQ
            if question_type == '0':
                create_mcq_question(self.request, question)

            # Either/Or
            elif question_type == '1':
                create_eo_option(self.request,question)

            # Short Answer
            elif question_type == '2':
                create_sa_question(self.request, question)

            # Essay
            elif question_type == '3':
                create_essay_question(self.request, question)

            # Text Filler
            elif question_type == '4':
                text = self.request.POST.get('tf_text')
                # TextFiller.objects.create(question=question, text=text)

            else:
                raise ValueError("Invalid question type submitted.")
        quiz.recalculate_maximum_marks()
        return super().form_valid(form)


    def get_success_url(self):
        return reverse('create_question', kwargs={'quiz_id': self.kwargs.get('quiz_id')})

@login_required(login_url='/users/login/')
@user_passes_test(lambda u: u.is_staff_member, login_url='/users/login/')
def get_question_partial(request):
    question_type = request.GET.get('question_type')
    if question_type == '0':
        return render(request,'partials/mcq_partial.html')
    elif question_type == '1':
        return render(request,'partials/either_or_partial.html')
    elif question_type == '2':
        return render(request,"partials/short_answer_partial.html")
    elif question_type == '3':
        return render(request,'partials/essay_partial.html')
    elif question_type == '4':
        return render(request,'partials/text_filler_partial.html')
    else:
        return HttpResponse("")

@login_required(login_url='/users/login/')
@user_passes_test(lambda u: u.is_staff_member, login_url='/users/login/')
def add_mcq_options(request):
    return render(request, "partials/mcq_single_option.html")

@login_required(login_url='/users/login/')
@user_passes_test(lambda u: u.role == u.is_staff_member, login_url='/users/login/')
def get_either_or_partial(request):
    return render(request, "partials/either_or_partial.html")

class ViewQuestions(LoginRequiredMixin, UserPassesTestMixin,ListView):
    model = Question
    template_name = 'view_questions.html'

    # custom query for get
    def get_queryset(self):
        qs = QuizQuestion.objects.filter(quiz_id=self.kwargs.get('quiz_id'))
        qs = qs.order_by('order_sequence')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = get_object_or_404(Quiz, id=self.kwargs.get('quiz_id'))
        context['course'] = get_object_or_404(Course, id=context['quiz'].course_id)
        return context

    def test_func(self, **kwargs):
        return is_staff_and_enrolled(self.request, self.kwargs['quiz_id'])


class EditQuestion(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = QuizQuestion
    template_name = 'edit_question.html'
    context_object_name = 'quiz_question'

    # manually saving to leaving it empty
    fields = []

    def test_func(self):
        quiz_question = get_object_or_404(QuizQuestion, id=self.kwargs.get('pk'))
        return is_staff_and_enrolled(self.request, quiz_question.quiz_id)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz_question = self.get_object()

        # Pass the base question to the template
        question = quiz_question.question
        context['question'] = question

        # Pre-load the specific options based on type to fill out values
        if question.question_type == 0:  # MCQ
            context['mcq_options'] = question.mcqoption_set.all()
            # To grab isMultipleAnswers
            context['mcq_settings'] = context['mcq_options'].first()
        elif question.question_type == 1: #either or
            context['eo_options'] = question.eitheroroption_set.all()
        elif question.question_type == 2:  # Short Answer
            context['sa_options'] = question.shortanswerquestionoption
            if question.shortanswerquestionoption.required_words:
                words_display = ""
                for word in question.shortanswerquestionoption.required_words:
                    words_display += word+','
                context['words_display'] = words_display[:-1]

        elif question.question_type == 3:  #Essay
            context['essay_options'] = question.essayquestionoption
        return context

    def form_valid(self, form):
        question_type = self.request.POST.get('question_type')

        # (MCQ) Validation
        if question_type == '0':
            mcq_texts = self.request.POST.getlist('mcq_option_text')

            # at least two options
            if len(mcq_texts) < 2:
                form.add_error(None, 'Multiple Choice questions require at least two options.')
                return self.form_invalid(form)

            # any of the provided options empty or just spaces
            for text in mcq_texts:
                if not text or not text.strip():
                    form.add_error(None,
                                   'All Multiple Choice options must contain text. Blank options are not allowed.')
                    return self.form_invalid(form)

        # Either/Or Validation
        elif question_type == '1':
            eo_texts = self.request.POST.getlist('eo_label_text')

            # exactly two options
            if len(eo_texts) != 2:
                form.add_error(None, 'Either/Or questions must have exactly two options (e.g., True and False).')
                return self.form_invalid(form)

            # neither option can be blank
            for text in eo_texts:
                if not text or not text.strip():
                    form.add_error(None, 'Both Either/Or options must contain text. Blank labels are not allowed.')
                    return self.form_invalid(form)

        # Short Answer Validation
        elif question_type == '2':
            sa_answer = self.request.POST.get('sa_answer')
            if not sa_answer or not sa_answer.strip():
                form.add_error(None, 'You must provide an Acceptable / Model Answer for Short Answer questions.')
                return self.form_invalid(form)

        # Essay Validation
        # elif question_type == '3':
        #     essay_model_answer = self.request.POST.get('essay_model_answer')
        #     if not essay_model_answer or not essay_model_answer.strip():
        #         form.add_error(None, 'You must provide a Model Answer / Grading Rubric for Essay questions.')
        #         return self.form_invalid(form)

        with transaction.atomic():
            quiz_question = form.save(commit=False)
            quiz_question.save()

            question = quiz_question.question
            question.question_text = self.request.POST.get('question_text')
            question.general_feedback = self.request.POST.get('general_feedback')
            question.save()

            q_type = question.question_type

            # --- MULTIPLE CHOICE ---
            if q_type == 0:
                create_mcq_question(self.request, question)

            # --- EITHER / OR ---
            elif q_type == 1:
                create_eo_option(self.request, question)

            # --- SHORT ANSWER ---
            elif q_type == 2:
                create_sa_question(self.request, question)

            # --- ESSAY ---
            elif q_type == 3:
                create_essay_question(self.request, question)

            # --- TEXT FILLER --- NOT IMPLEMENTED
            elif q_type == 4:
                tf_opt, created = TextFiller.objects.get_or_create(question=question)

                tf_opt.text = self.request.POST.get('tf_text')
                tf_opt.maximum_mark = self.request.POST.get('tf_max_mark') or 0
                tf_opt.negative_mark = self.request.POST.get('tf_negative_mark') or 0
                tf_opt.save()

        quiz_question.quiz.recalculate_maximum_marks()
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect the teacher back to the Edit Quiz page
        return reverse('edit-quiz', kwargs={'pk': self.object.quiz_id})

@login_required(login_url='/users/login/')
@require_http_methods(["DELETE"]) # Block GET links
def delete_question(request, **kwargs):
    quiz_question = get_object_or_404(QuizQuestion, pk=kwargs['pk'])
    if not is_staff_and_enrolled(request,quiz_question.quiz_id):
        raise PermissionDenied("You are not enrolled in this module/course")

    quiz_question.delete()

    updated_questions = QuizQuestion.objects.filter(quiz_id=quiz_question.quiz_id)
    return render(request, 'partials/question_list_partial.html', {'questions': updated_questions})
@login_required(login_url='/users/login/')
@user_passes_test(lambda u: u.is_staff_member, login_url='/users/login/')
def question_bank(request, course_id):
    if not is_staff_and_enrolled(request,course_id,id_type='course'):
        raise PermissionDenied("You are not enrolled in this module/course")


    course = get_object_or_404(Course, pk=course_id)
    questions = QuizQuestion.objects.filter(quiz__course=course)
    return render(request, 'question_bank.html', {'questions': questions, 'course': course})

@login_required(login_url='/users/login/')
@user_passes_test(lambda u: u.is_staff_member, login_url='/users/login/')
def search_questions(request, course_id):
    if not is_staff_and_enrolled(request,course_id,id_type='course'):
        raise PermissionDenied("You are not enrolled in this module/course")

    course = get_object_or_404(Course, id=course_id)
    questions = QuizQuestion.objects.filter(quiz__course=course)

    search = request.GET.get('search', '')

    if search:
        questions = questions.filter(
            Q(question__question_text__icontains=search) |
            Q(question__question_type__icontains=search)
        )
    return render(request,"partials/question_bank_record_partial.html",{"questions":questions})

# ---------- HELPER FUNCTIONS ----------
def create_mcq_question(request, question):
    allow_multiple = request.POST.get('mcq_isMultipleAnswer') == 'on'
    options_texts = request.POST.getlist('mcq_option_text')
    max_marks = request.POST.getlist('mcq_max_mark')
    negative_marks = request.POST.getlist('mcq_negative_mark')
    option_feedbacks = request.POST.getlist('mcq_option_feedback')
    is_correct_list = request.POST.getlist('mcq_is_correct_list')

    question.mcqoption_set.all().delete()

    for index, text in enumerate(options_texts):
        McqOption.objects.create(
            question=question,
            option_text=text,
            maximum_mark=max_marks[index] if max_marks[index] else 0,
            negative_mark=negative_marks[index] if negative_marks[index] else 0,
            option_feedback=option_feedbacks[index],
            order_sequence=index,
            isMultipleAnswers=allow_multiple,
            is_correct=(is_correct_list[index] == 'True')
        )

def create_eo_option(request,question):
    label_texts = request.POST.getlist('eo_label_text')
    specific_feedbacks = request.POST.getlist('eo_specific_feedback')
    max_marks = request.POST.getlist('eo_max_mark')
    negative_marks = request.POST.getlist('eo_negative_mark')
    is_correct_list = request.POST.getlist('eo_is_correct_list')

    question.eitheroroption_set.all().delete()

    for index, text in enumerate(label_texts):
        EitherOrOption.objects.create(
            question=question,
            label=text,
            order_sequence=index,
            is_correct=(is_correct_list[index] == 'True'),
            specific_feedback=specific_feedbacks[index],
            maximum_mark=max_marks[index] if max_marks[index] else 0,
            negative_mark=negative_marks[index] if negative_marks[index] else 0
        )

def create_sa_question(request, question):
    max_words = request.POST.get('sa_max_word')
    use_case = request.POST.get('sa_use_case')
    answer = request.POST.get('sa_answer')
    max_marks = request.POST.get('sa_max_mark')
    negative_marks = request.POST.get('sa_negative_mark')
    is_auto_marked = request.POST.get('sa_is_auto_marked') == '1'
    exact_match = request.POST.get('sa_exact_match_only') == '1'


    required_words = request.POST.get('sa_required_keywords')
    cleaned_words = []
    if required_words:
        cleaned_words = [w.strip() for w in required_words.split(',') if w.strip()]

    if getattr(question, 'shortanswerquestionoption',False):
        question.shortanswerquestionoption.delete()

    ShortAnswerQuestionOption.objects.create(
        question=question,
        maximum_word_count=max_words if max_words else None,
        use_case=(use_case == '1'),
        answer_text=answer,
        maximum_mark=max_marks if max_marks else 0,
        negative_mark=negative_marks if negative_marks else 0,
        required_words=cleaned_words,
        is_auto_mark=is_auto_marked,
        use_exact_answer=exact_match
    )


def create_essay_question(request, question):
    min_words = request.POST.get('essay_minword')
    max_words = request.POST.get('essay_maxword')
    max_marks = request.POST.get('essay_max_mark')
    negative_marks = request.POST.get('essay_negative_mark')
    model_answer = request.POST.get('essay_model_answer')
    is_auto_mark = request.POST.get('essay_is_auto_marked') == '1'

    essay_option, created = EssayQuestionOption.objects.get_or_create(question=question)

    essay_option.minimum_word_count = min_words if min_words else 0
    essay_option.maximum_word_count = max_words if max_words else None
    essay_option.maximum_mark = max_marks if max_marks else 0
    essay_option.negative_mark = negative_marks if negative_marks else 0
    essay_option.model_answer = model_answer if model_answer else "No model answer provided"
    essay_option.is_auto_mark = is_auto_mark


    clear_rubric = request.POST.get('clear_essay_rubric')
    if clear_rubric == 'on' and essay_option.marking_rubric:
        essay_option.marking_rubric.delete(save=False)
        essay_option.marking_rubric = None

    new_rubric_file = request.FILES.get('essay_marking_rubric')
    if new_rubric_file:
        if essay_option.marking_rubric:
            essay_option.marking_rubric.delete(save=False)
        essay_option.marking_rubric = new_rubric_file
    essay_option.save()


# ---------- HELPER FUNCTIONS ----------
def is_staff_and_enrolled(request, quiz_id, id_type='quiz'):
    if request.user.is_admin:
        return True
    is_enrolled = user_is_enrolled(request, quiz_id, id_type)
    return is_enrolled and request.user.is_staff_member


def user_is_enrolled(request, quiz_or_course_id, id_type='quiz'):
    if id_type == 'quiz':
        quiz = get_object_or_404(Quiz, id=quiz_or_course_id)
        course = get_object_or_404(Course, id=quiz.course_id)
    else:
        course = get_object_or_404(Course, id=quiz_or_course_id)
    return course.enrollment.filter(id=request.user.id).exists()