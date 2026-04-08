from datetime import timedelta

from django.db.models import UniqueConstraint, Q
from django.utils import timezone

from django.db import models

from com3610 import settings
from courses.models import Course
from questions.models import Question
from utils.question_status import QuestionStatus


# Create your models here.

class Quiz (models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    name = models.CharField(max_length=100)
    introduction = models.TextField(null=True, blank=True)
    # TODO password
    # TODO Subnet
    overall_feedback = models.TextField(null=True, blank=True)
    shuffle_questions = models.BooleanField(default=False)
    shuffle_answers = models.BooleanField(default=False)
    maximum_marks = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    # Blank means no restrictions
    open_date = models.DateTimeField(null=True, blank=True)
    close_date = models.DateTimeField(null=True, blank=True)
    # Blank means no timelimit
    time_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # -1 should be unlimited or leave blank for unlimited
    maximum_attempts = models.IntegerField(null=True, blank=True, default=-1)
    delay_between_attempts = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # TODO grading_method

    # Review the attempt
    review_attempt = models.BooleanField(default=False)
    review_right_answer = models.BooleanField(default=False)
    review_marks = models.BooleanField(default=False)

    #specific feedback regarding selected options
    review_specific_feedback = models.BooleanField( default=False)
    # general feedback for the question
    review_general_feedback = models.BooleanField( default=False)
    # Overall feedback for the quiz
    review_overall_feedback = models.BooleanField( default=False)

    show_user_picture = models.BooleanField( default=False)

    anonymise_student = models.BooleanField( default=False)
    anonymise_marker = models.BooleanField(default=False)

class QuizQuestion (models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    # TODO question_properties + update DB diagram - maybe we dont even need this
    order_sequence = models.IntegerField()
    # Can update and override feedback from Question
    general_feedback = models.CharField(null=True, blank=True)

class Attempt (models.Model):
    # each attempt is linked to one quiz
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='quiz_attempt', on_delete=models.CASCADE)

    attempt_count = models.IntegerField(null=True, blank=True, default=0)
    status = models.IntegerField(choices=QuestionStatus.choices(), null=True, blank=True, default=0)
    total_marks_given = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    marked_at = models.DateTimeField(null=True, blank=True)

    start_time = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    @property
    def deadline(self):
        return self.start_time + timedelta(minutes=float(self.quiz.time_limit))

    @property
    def is_time_up(self):
        return timezone.now() > self.deadline

class Response (models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    attempt = models.ForeignKey(Attempt, related_name='responses' ,on_delete=models.CASCADE)

    status = models.IntegerField(choices=QuestionStatus.choices(), null=True, blank=True, default=0)
    answer_given = models.TextField(null=True, blank=True) #if the question required text answer
    marks_given = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        #student can only have ONE answer per question per attempt
        unique_together = ('attempt', 'question')

class ResponseOption(models.Model):
    """For MCQ/EO question response - skipped if question is text only, just store the id of the options chosen"""
    response = models.ForeignKey(Response,related_name='selected_options', on_delete=models.CASCADE)
    mcq_option = models.ForeignKey('questions.McqOption', on_delete=models.CASCADE, null=True, blank=True)
    eo_option = models.ForeignKey('questions.EitherOrOption', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        constraints = [
            # blocks the db from saving a second EO option for the same response
            UniqueConstraint(
                fields=['response'],
                condition=Q(eo_option__isnull=False),
                name='unique_eo_per_response'
            )
        ]