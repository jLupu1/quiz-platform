from django.db import models
from django.contrib.postgres.fields import ArrayField
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

    def get_badge_color(self):
        """Returns the specific Bootstrap classes for the question type."""
        colors = {
            0: 'bg-dark text-white',  # MCQ
            1: 'bg-warning text-white',  # Either/Or
            2: 'bg-info text-white',  # Short Answer
            3: 'bg-success text-white',  # Essay
            4: 'bg-primary text-white'  # Text Filler
        }
        # Returns the color, or defaults to secondary if something goes wrong
        return colors.get(self.question_type, 'bg-secondary text-white')

    def calc_question_max_mark(self):
        """Calculates the maximum mark value for given question type."""
        total = 0
        if self.question_type == QuestionType.MCQ:
            options = self.mcqoption_set.all()
            for option in options:
                total += option.maximum_mark
            return total
        elif self.question_type == QuestionType.EITHER_OR:
            options = self.eitheroroption_set.all()
            for option in options:
                total += option.maximum_mark
            return total
        elif self.question_type == QuestionType.SHORT_ANSWER:
            return self.shortanswerquestionoption.maximum_mark
        elif self.question_type == QuestionType.ESSAY_QUESTION:
            return self.essayquestionoption.maximum_mark
        else:
            return False

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
    minimum_word_count = models.IntegerField(default=0)
    maximum_word_count = models.IntegerField()
    maximum_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    model_answer = models.CharField(null=True, blank=True)
    negative_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)

class ShortAnswerQuestionOption(models.Model):
    question = models.OneToOneField('Question', on_delete=models.CASCADE)
    maximum_word_count = models.IntegerField(null=True, blank=True)
    use_case = models.BooleanField(default=False)
    answer_text = models.CharField(null=False)
    maximum_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    negative_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    is_auto_mark = models.BooleanField(default=False)
    use_exact_answer = models.BooleanField(default=False)
    required_words = ArrayField(models.CharField(max_length=50), null=True, blank=True, default=list)

class TextFiller(models.Model):
    question = models.OneToOneField('Question', on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)
    maximum_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    negative_mark = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    # word_list





