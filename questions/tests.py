from django.test import TestCase
from decimal import Decimal
from questions.models import (
    Question, QuestionType, McqOption, EitherOrOption,
    ShortAnswerQuestionOption, EssayQuestionOption
)

class QuestionLogicTests(TestCase):
    def setUp(self):
        # Create base questions of different types
        self.mcq_q = Question.objects.create(
            question_text="What is HTTP?", question_type=QuestionType.MCQ
        )
        self.eo_q = Question.objects.create(
            question_text="HTML is a programming language.", question_type=QuestionType.EITHER_OR
        )
        self.sa_q = Question.objects.create(
            question_text="Define REST.", question_type=QuestionType.SHORT_ANSWER
        )
        self.essay_q = Question.objects.create(
            question_text="Discuss WebSockets.", question_type=QuestionType.ESSAY_QUESTION
        )

    def test_badge_colors(self):
        """Test that the UI badge colors match the question type."""
        self.assertEqual(self.mcq_q.get_badge_color(), 'bg-dark text-white')
        self.assertEqual(self.eo_q.get_badge_color(), 'bg-warning text-white')
        self.assertEqual(self.sa_q.get_badge_color(), 'bg-info text-white')
        self.assertEqual(self.essay_q.get_badge_color(), 'bg-success text-white')

    def test_calc_max_mark_mcq(self):
        """MCQ max mark should sum the maximum_mark of its options."""
        McqOption.objects.create(question=self.mcq_q, option_text="Protocol", is_correct=True, maximum_mark=2.00)
        McqOption.objects.create(question=self.mcq_q, option_text="Language", is_correct=False, maximum_mark=0.00)

        self.assertEqual(self.mcq_q.calc_question_max_mark(), 2.00)

    def test_calc_max_mark_either_or(self):
        """Either/Or max mark should sum the maximum_mark of its options."""
        EitherOrOption.objects.create(question=self.eo_q, label="True", is_correct=False, maximum_mark=0.00)
        EitherOrOption.objects.create(question=self.eo_q, label="False", is_correct=True, maximum_mark=1.50)

        self.assertEqual(self.eo_q.calc_question_max_mark(), 1.50)

    def test_calc_max_mark_short_answer(self):
        """Short answer max mark directly references the OneToOne option."""
        ShortAnswerQuestionOption.objects.create(
            question=self.sa_q,
            answer_text="Representational State Transfer",
            maximum_mark=5.00
        )

        self.assertEqual(self.sa_q.calc_question_max_mark(), 5.00)

    def test_calc_max_mark_essay(self):
        """Essay max mark directly references the OneToOne option."""
        EssayQuestionOption.objects.create(
            question=self.essay_q,
            maximum_mark=10.00,
            minimum_word_count=100
        )

        self.assertEqual(self.essay_q.calc_question_max_mark(), 10.00)

    def test_calc_max_mark_unconfigured(self):
        """If a text filler question type doesn't have a max mark calculation defined, it should return False."""
        filler_q = Question.objects.create(
            question_text="Fill in the blank.", question_type=QuestionType.TEXT_FILLER
        )
        self.assertFalse(filler_q.calc_question_max_mark())