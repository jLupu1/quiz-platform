from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from users.models import User, Arrangement
from courses.models import Course
from quizzes.models import Quiz, QuizQuestion, Attempt, Response, ResponseOption
from questions.models import Question, QuestionType, McqOption


class QuizAvailabilityTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(code="CS101", name="Intro to CS")
        self.quiz = Quiz.objects.create(
            course=self.course,
            name="Test Quiz",
            status=Quiz.QuizStatus.CLOSED
        )
        # Quizzes return False for availability if they have no questions!
        self.question = Question.objects.create(
            question_text="Sample", question_type=QuestionType.MCQ
        )
        QuizQuestion.objects.create(quiz=self.quiz, question=self.question, order_sequence=1)

    def test_quiz_availability_closed(self):
        """A closed quiz should not be available regardless of dates."""
        self.quiz.status = Quiz.QuizStatus.CLOSED
        self.quiz.save()
        self.assertFalse(self.quiz.is_currently_available)

    def test_quiz_availability_manually_open(self):
        """A manually opened quiz should always be available."""
        self.quiz.status = Quiz.QuizStatus.OPEN
        self.quiz.save()
        self.assertTrue(self.quiz.is_currently_available)

    def test_quiz_availability_scheduled(self):
        """Test scheduled quizzes against timezone.now()"""
        self.quiz.status = Quiz.QuizStatus.SCHEDULED
        now = timezone.now()

        # Past window (should be closed)
        self.quiz.open_date = now - timedelta(days=2)
        self.quiz.close_date = now - timedelta(days=1)
        self.quiz.save()
        self.assertFalse(self.quiz.is_currently_available)

        # Active window (should be open)
        self.quiz.open_date = now - timedelta(days=1)
        self.quiz.close_date = now + timedelta(days=1)
        self.quiz.save()
        self.assertTrue(self.quiz.is_currently_available)


class AttemptDeadlineTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(code="CS101", name="Intro to CS")
        self.quiz = Quiz.objects.create(
            course=self.course, name="Test Quiz", time_limit=30.00
        )
        self.standard_user = User.objects.create(username='std', email='std@test.com')

        self.accommodated_user = User.objects.create(username='acc', email='acc@test.com')
        arrangement = Arrangement.objects.create(extra_time=25.00)  # 25% extra time
        self.accommodated_user.arrangement = arrangement
        self.accommodated_user.save()

    def test_standard_deadline(self):
        """Standard users should get exactly the time limit."""
        attempt = Attempt.objects.create(quiz=self.quiz, user=self.standard_user)
        expected_deadline = attempt.start_time + timedelta(minutes=30)

        self.assertEqual(attempt.deadline, expected_deadline)

    def test_accommodated_deadline(self):
        """Users with extra time should get mathematically adjusted deadlines."""
        attempt = Attempt.objects.create(quiz=self.quiz, user=self.accommodated_user)

        # 30 mins + 25% = 37.5 mins
        expected_deadline = attempt.start_time + timedelta(minutes=37.5)

        self.assertEqual(attempt.deadline, expected_deadline)


class AutoGradingTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(code="CS101", name="Intro to CS")
        self.quiz = Quiz.objects.create(course=self.course, name="Test Quiz")
        self.user = User.objects.create(username='student1')

        # Create an MCQ Question
        self.question = Question.objects.create(
            question_text="What is 2+2?",
            question_type=QuestionType.MCQ
        )
        self.quiz_question = QuizQuestion.objects.create(
            quiz=self.quiz, question=self.question, order_sequence=1
        )

        # Create Options
        self.correct_opt = McqOption.objects.create(
            question=self.question, option_text="4", is_correct=True,
            maximum_mark=2.00, negative_mark=0.50
        )
        self.wrong_opt = McqOption.objects.create(
            question=self.question, option_text="5", is_correct=False,
            maximum_mark=2.00, negative_mark=0.50
        )

        self.attempt = Attempt.objects.create(quiz=self.quiz, user=self.user)

    def test_auto_grade_correct_mcq(self):
        """A correct response should award maximum_mark."""
        response = Response.objects.create(quiz_question=self.quiz_question, attempt=self.attempt)
        ResponseOption.objects.create(response=response, mcq_option=self.correct_opt)

        response.auto_grade()
        self.assertEqual(response.marks_given, 2.00)

    def test_auto_grade_incorrect_mcq(self):
        """An incorrect response should deduct negative_mark, but clamp to 0."""
        response = Response.objects.create(quiz_question=self.quiz_question, attempt=self.attempt)
        ResponseOption.objects.create(response=response, mcq_option=self.wrong_opt)

        response.auto_grade()
        # It deducts 0.50, but max(0, -0.50) means it should clamp to 0
        self.assertEqual(response.marks_given, 0.00)

    def test_auto_grade_skipped_question(self):
        """A skipped question should result in 0 marks, not an error."""
        response = Response.objects.create(quiz_question=self.quiz_question, attempt=self.attempt)
        # Deliberately NOT adding a ResponseOption

        response.auto_grade()
        self.assertEqual(response.marks_given, 0.00)