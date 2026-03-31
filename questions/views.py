from unittest.result import failfast

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from questions.models import Question, McqOption, ShortAnswerQuestionOption, EssayQuestionOption, EitherOrOption
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
        for added_question in context['added_questions']:
            print(added_question.question.question_text)

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
                allow_multiple = self.request.POST.get('mcq_isMultipleAnswer') == 'on'

                options_texts = self.request.POST.getlist('mcq_option_text')
                print(options_texts)
                max_marks = self.request.POST.getlist('mcq_max_mark')
                negative_marks = self.request.POST.getlist('mcq_negative_mark')
                option_feedbacks = self.request.POST.getlist('mcq_option_feedback')
                is_correct_list = self.request.POST.getlist('mcq_is_correct_list')

                for index, text in enumerate(options_texts):
                    print(options_texts[index],max_marks[index],negative_marks[index],option_feedbacks,is_correct_list[index])
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
            # Either/Or
            elif question_type == '1':
                label_texts = self.request.POST.getlist('eo_label_text')
                specific_feedbacks = self.request.POST.getlist('eo_specific_feedback')
                max_marks = self.request.POST.getlist('eo_max_mark')
                negative_marks = self.request.POST.getlist('eo_negative_mark')
                is_correct_list = self.request.POST.getlist('eo_is_correct_list')

                for index, text in enumerate(label_texts):
                    id = EitherOrOption.objects.create(
                        question=question,
                        option_text=text,
                        order_sequence=index,
                        is_correct=(is_correct_list[index] == 'True'),
                        specific_feedback=specific_feedbacks[index],
                        maximum_mark=max_marks[index] if max_marks[index] else 0,
                        negative_mark=negative_marks[index] if negative_marks[index] else 0
                    ).id
            # Short Answer
            elif question_type == '2':
                max_words = self.request.POST.get('sa_max_word')
                use_case = self.request.POST.get('sa_use_case')
                answer = self.request.POST.get('sa_answer')
                max_marks = self.request.POST.get('sa_max_mark')
                negative_marks = self.request.POST.get('sa_negative_mark')

                ShortAnswerQuestionOption.objects.create(
                    question=question,
                    maximum_word_length=max_words if max_words else None,
                    use_case=(use_case == '1'),
                    answer_text=answer,
                    maximum_mark=max_marks if max_marks else 0,
                    negative_mark=negative_marks if negative_marks else 0,
                )
            # Essay
            elif question_type == '3':
                min_words = self.request.POST.get('essay_minword')
                max_words = self.request.POST.get('essay_maxword')
                max_marks = self.request.POST.get('essay_max_mark')
                negative_marks = self.request.POST.get('essay_negative_mark')
                model_answer = self.request.POST.get('essay_model_answer')

                EssayQuestionOption.objects.create(
                    question=question,
                    minimum_word_length=min_words if min_words else None,
                    maximum_word_length=max_words if max_words else None,
                    maximum_mark=max_marks if max_marks else 0,
                    negative_mark=negative_marks if negative_marks else 0,
                    model_answer=model_answer,
                )
            # Text Filler
            elif question_type == '4':
                text = self.request.POST.get('tf_text')
                # TextFiller.objects.create(question=question, text=text)

            else:
                raise ValueError("Invalid question type submitted.")

        return super().form_valid(form)


    def get_success_url(self):
        return reverse('create_question', kwargs={'quiz_id': self.kwargs.get('quiz_id')})

# TODO link backend to frontend. Save the question and redicret to add a new one. create a finish button when teacher is happy
@login_required(login_url='/users/login/')
@user_passes_test(lambda u: u.role == u.is_staff_member, login_url='/users/login/')
def get_question_partial(request):
    question_type = request.GET.get('question_type')
    print(question_type)
    if question_type == '0':
        return render(request,'partials/mcq_partial.html')
    elif question_type == '1':
        return render(request,'partials/either_or_partial.html',{'n':'12'}) #1,2 to create options
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