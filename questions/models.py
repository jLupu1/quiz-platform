from django.db import models
from enum import IntEnum

class QuestionType(models.IntegerChoices):
    MCQ = 0, 'Multiple Choice (MCQ)'
    EITHER_OR = 1, 'Either/Or (True/False)'
    SHORT_ANSWER = 2, 'Short Answer'
    ESSAY_QUESTION = 3, 'Essay'
    TEXT_FILLER = 4, 'Text Filler (Fill in blanks)'

# Create your models here.
class Question (models.Model):
    question_text = models.CharField(null=False, blank=False, default="")
    question_type = models.IntegerField(choices=QuestionType.choices)
    general_feedback = models.CharField(null=True, blank=True) #ovverrideable through quizQuestion

class McqOption(models.Model):
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    option_text = models.CharField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    order_sequence = models.IntegerField(default=0)
    option_feedback = models.CharField(null=True, blank=True)
    maximum_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    negative_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    isMultipleAnswers = models.BooleanField(default=False)

class EitherOrOption(models.Model):
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    label = models.CharField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    order_sequence = models.IntegerField(default=0)
    specific_feedback = models.CharField(null=True, blank=True)
    maximum_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    negative_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)

class EssayQuestionOption(models.Model):
    question = models.OneToOneField('Question', on_delete=models.CASCADE)
    minimum_word_length = models.IntegerField(default=0)
    maximum_word_length = models.IntegerField()
    maximum_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    model_answer = models.CharField(null=True, blank=True)
    negative_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)

class ShortAnswerQuestionOption(models.Model):
    question = models.OneToOneField('Question', on_delete=models.CASCADE)
    maximum_word_length = models.IntegerField()
    use_case = models.BooleanField(default=False)
    answer_text = models.CharField(null=False, blank=False)
    maximum_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    negative_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)

class TextFiller(models.Model):
    question = models.OneToOneField('Question', on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)
    maximum_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    negative_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    # word_list





