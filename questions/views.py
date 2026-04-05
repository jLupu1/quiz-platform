from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from courses.models import Course
from questions.models import Question, McqOption, ShortAnswerQuestionOption, EssayQuestionOption, EitherOrOption, \
    TextFiller
from quizzes.models import Quiz, QuizQuestion
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
        context['added_questions'] = QuizQuestion.objects.filter(quiz=context['quiz'])

        return context

    def form_valid(self, form):
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

            question_type = self.request.POST.get('question_type')

            # Due to how question types are set up using enums and frontend limitations
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
@user_passes_test(lambda u: u.role == u.is_staff_member, login_url='/users/login/')
def add_mcq_options(request):
    return render(request, "partials/mcq_single_option.html")

@login_required(login_url='/users/login/')
@user_passes_test(lambda u: u.role == u.is_staff_member, login_url='/users/login/')
def get_either_or_partial(request):
    return render(request, "partials/either_or_partial.html")

class ViewQuestions(LoginRequiredMixin, UserPassesTestMixin,ListView):
    model = Question
    template_name = 'view_questions.html'

    def get_queryset(self):
        qs = QuizQuestion.objects.filter(quiz_id=self.kwargs.get('quiz_id'))
        qs = qs.order_by('order_sequence')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = get_object_or_404(Quiz, id=self.kwargs.get('quiz_id'))
        print(context['quiz'])
        context['course'] = get_object_or_404(Course, id=context['quiz'].course_id)
        return context

    def test_func(self, **kwargs):
        quiz = get_object_or_404(Quiz, id=self.kwargs.get('quiz_id'))
        course = get_object_or_404(Course, id=quiz.course_id)
        is_enrolled = course.enrollment.filter(id=self.request.user.id).exists()
        return self.request.user.is_admin or is_enrolled


class EditQuestion(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = QuizQuestion
    template_name = 'edit_question.html'
    context_object_name = 'quiz_question'

    # manually saving to leaving it empty
    fields = []

    def test_func(self):
        quiz_question = get_object_or_404(QuizQuestion, id=self.kwargs.get('pk'))
        quiz = get_object_or_404(Quiz, id=quiz_question.quiz_id)
        course = get_object_or_404(Course, id=quiz.course_id)
        # Check if user is staff or enrolled
        is_enrolled = course.enrollment.filter(id=self.request.user.id).exists()
        return self.request.user.is_staff_member or is_enrolled

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz_question = self.get_object()

        # Pass the base question to the template
        question = quiz_question.question
        context['question'] = question

        # Pre-load the specific options based on type so the HTML can fill the values!
        if question.question_type == 0:  # MCQ
            context['mcq_options'] = question.mcqoption_set.all()
            # To grab isMultipleAnswers
            context['mcq_settings'] = context['mcq_options'].first()
        elif question.question_type == 1: #either or
            context['eo_options'] = question.eitheroroption_set.all()
            print(context['eo_options'])
        elif question.question_type == 2:  # Short Answer
            context['short_answer'] = question.shortanswerquestionoption_set.first()
        # ... add others here as needed for your template context ...

        return context

    def form_valid(self, form):
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
                sa_opt, created = ShortAnswerQuestionOption.objects.get_or_create(question=question)

                max_words = self.request.POST.get('sa_max_word')

                sa_opt.maximum_word_length = max_words if max_words else 0
                sa_opt.use_case = (self.request.POST.get('sa_use_case') == '1')
                sa_opt.answer_text = self.request.POST.get('sa_answer')
                sa_opt.maximum_mark = self.request.POST.get('sa_max_mark') or 0
                sa_opt.negative_mark = self.request.POST.get('sa_negative_mark') or 0
                sa_opt.save()

            # --- ESSAY ---
            elif q_type == 3:
                essay_opt, created = EssayQuestionOption.objects.get_or_create(question=question)

                min_words = self.request.POST.get('essay_minword')
                max_words = self.request.POST.get('essay_maxword')

                essay_opt.minimum_word_length = min_words if min_words else 0
                essay_opt.maximum_word_length = max_words if max_words else 0
                essay_opt.maximum_mark = self.request.POST.get('essay_max_mark') or 0
                essay_opt.negative_mark = self.request.POST.get('essay_negative_mark') or 0
                essay_opt.model_answer = self.request.POST.get('essay_model_answer')
                essay_opt.save()

            # --- TEXT FILLER ---
            elif q_type == 4:
                tf_opt, created = TextFiller.objects.get_or_create(question=question)

                tf_opt.text = self.request.POST.get('tf_text')
                tf_opt.maximum_mark = self.request.POST.get('tf_max_mark') or 0
                tf_opt.negative_mark = self.request.POST.get('tf_negative_mark') or 0
                tf_opt.save()

        return super().form_valid(form)

    def get_success_url(self):
        # Redirect the teacher back to the split-screen Edit Quiz page
        return reverse('edit-quiz', kwargs={'pk': self.object.quiz_id})


# ---------- HELPER FUNCTIONS ----------
def create_mcq_question(request, question):
    allow_multiple = request.POST.get('mcq_isMultipleAnswer') == 'on'
    options_texts = request.POST.getlist('mcq_option_text')
    max_marks = request.POST.getlist('mcq_max_mark')
    negative_marks = request.POST.getlist('mcq_negative_mark')
    option_feedbacks = request.POST.getlist('mcq_option_feedback')
    is_correct_list = request.POST.getlist('mcq_is_correct_list')

    # For when edit is done - won't have any side effects for new questions
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
    print(label_texts, specific_feedbacks, max_marks, negative_marks, is_correct_list)

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

    ShortAnswerQuestionOption.objects.create(
        question=question,
        maximum_word_length=max_words if max_words else None,
        use_case=(use_case == '1'),
        answer_text=answer,
        maximum_mark=max_marks if max_marks else 0,
        negative_mark=negative_marks if negative_marks else 0,
    )

def create_essay_question(request, question):
    min_words = request.POST.get('essay_minword')
    max_words = request.POST.get('essay_maxword')
    max_marks = request.POST.get('essay_max_mark')
    negative_marks = request.POST.get('essay_negative_mark')
    model_answer = request.POST.get('essay_model_answer')

    EssayQuestionOption.objects.create(
        question=question,
        minimum_word_length=min_words if min_words else None,
        maximum_word_length=max_words if max_words else None,
        maximum_mark=max_marks if max_marks else 0,
        negative_mark=negative_marks if negative_marks else 0,
        model_answer=model_answer,
    )


