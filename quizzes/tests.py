from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from django.test import TestCase, Client
from nltk.sem.relextract import roles_demo

from users.models import User, Arrangement, UserRole
from courses.models import Course
from quizzes.models import Quiz, QuizQuestion, Attempt, Response, ResponseOption
from questions.models import Question, QuestionType, McqOption, ShortAnswerQuestionOption, EitherOrOption, \
    EssayQuestionOption


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


class BaseQuizViewTest(TestCase):
    """Base setup class so we don't repeat user/course creation in every test"""

    def setUp(self):
        self.client = Client()

        # 1. Create Users
        self.admin = User.objects.create_user(username='admin', password='password123', role=UserRole.ADMIN, email='admin@email.com')
        self.teacher = User.objects.create_user(username='teacher', password='password123', role=UserRole.TEACHER, email='tchr@email.com')
        self.teacher_unenrolled = User.objects.create_user(
            username='teacher2', password='password123', role=UserRole.TEACHER,email='tchr2@gmail.com'
        )
        self.student = User.objects.create_user(username='student', password='password123', role=UserRole.STUDENT, email='stud@email.com')
        self.student2 = User.objects.create_user(username='student2', password='password123', role=UserRole.STUDENT, email='stud2@email.com')

        self.snooping_student = User.objects.create_user(username='snooper', password='password123', role=UserRole.STUDENT,email='snooping_stud@email.com')

        # 2. Create Course & Enrollments
        self.course = Course.objects.create(name="Web Dev", code="COM101")
        self.course.enrollment.add(self.teacher, self.student, self.snooping_student)

        # 3. Create a Base Quiz & Question
        self.quiz = Quiz.objects.create(
            course=self.course, name="Midterm", status=1,
            maximum_attempts=2, time_limit=60.00
        )
        self.question = Question.objects.create(question_text="Define HTML", question_type=QuestionType.SHORT_ANSWER)
        ShortAnswerQuestionOption.objects.create(question=self.question, maximum_mark=5.00, answer_text="HyperText")
        self.quiz_question = QuizQuestion.objects.create(quiz=self.quiz, question=self.question, order_sequence=1)


#  ----- Teacher management of quizzes
class QuizManagementViewTests(BaseQuizViewTest):
    def test_create_quiz_success_and_routing(self):
        """Test creating a quiz correctly redirects to the create_question view"""
        self.client.login(username='teacher', password='password123')
        url = reverse('create-quiz', kwargs={'course_id': self.course.id})

        data = {
            'name': 'Final Exam', 'introduction': 'Good luck!', 'status': 0,
            'maximum_attempts': 1, 'time_limit': 120, 'shuffle_questions': 'on'
        }
        response = self.client.post(url, data)

        # Should redirect to the question builder
        new_quiz = Quiz.objects.get(name='Final Exam')
        self.assertRedirects(response, reverse('create_question', kwargs={'quiz_id': new_quiz.id}))

    def test_edit_quiz_validation_dates(self):
        """Test that close_date cannot be before open_date"""
        self.client.login(username='teacher', password='password123')
        url = reverse('edit-quiz', kwargs={'pk': self.quiz.id})

        now = timezone.now()
        data = {
            'name': 'Midterm', 'open_date': now.strftime('%Y-%m-%dT%H:%M'),
            'close_date': (now - timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')  # Invalid!
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'close_date', 'The close date must be after the open date.')

    def test_delete_quiz_permissions(self):
        """Test that only enrolled teachers/admins can delete via DELETE request"""
        url = reverse('delete_quiz', kwargs={'pk': self.quiz.id})

        self.client.login(username='student', password='password123')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(username='teacher', password='password123')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Quiz.objects.filter(id=self.quiz.id).exists())


# Student taking quiz
class QuizStudentViewTests(BaseQuizViewTest):
    def test_quiz_landing_page_logic(self):
        """Test max attempts logic and resuming attempts"""
        self.client.login(username='student', password='password123')
        url = reverse('quiz_landing', kwargs={'quiz_id': self.quiz.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['reached_max'])

        response = self.client.post(url)
        attempt = Attempt.objects.get(user=self.student, quiz=self.quiz)
        self.assertRedirects(response, reverse('take_quiz', kwargs={'attempt_id': attempt.id}))

    def test_password_checker_view(self):
        """Test the password protection gate"""
        self.quiz.password = "SECRET123"
        self.quiz.save()

        self.client.login(username='student', password='password123')
        url = reverse('quiz_password_prompt', kwargs={'quiz_id': self.quiz.id})

        # Bad Password
        response = self.client.post(url, {'quiz_password': 'WRONG'})
        self.assertContains(response, "Incorrect password")

        # Good Password
        response = self.client.post(url, {'quiz_password': 'SECRET123'})
        self.assertTrue('HX-Redirect' in response)

    def test_submit_quiz_double_submission(self):
        """Test that a completed quiz cannot be submitted twice"""
        self.client.login(username='student', password='password123')
        attempt = Attempt.objects.create(quiz=self.quiz, user=self.student, is_completed=True)
        url = reverse('submit_quiz', kwargs={'attempt_id': attempt.id})

        response = self.client.post(url)

        self.assertRedirects(response, reverse('quiz_results', kwargs={'attempt_id': attempt.id}))


# ---- Grading and reviewing
class QuizGradingViewTests(BaseQuizViewTest):
    def setUp(self):
        super().setUp()
        self.attempt = Attempt.objects.create(quiz=self.quiz, user=self.student, is_completed=True)
        self.response = Response.objects.create(attempt=self.attempt, quiz_question=self.quiz_question,
                                                answer_given="Hyper")
        self.url = reverse('update_student_marks', kwargs={'response_id': self.response.id})

    def test_update_student_marks_validation(self):
        """Test the manual teacher grading view catches over-grading and negative grading"""
        self.client.login(username='teacher', password='password123')

        # Max marks for this question is 5.00

        # 1. Test Negative Marks
        res = self.client.post(self.url, {'new_marks': '-1.00'})
        self.assertContains(res, "Marks cannot be negative!")

        # 2. Test Exceeding Max Marks
        res = self.client.post(self.url, {'new_marks': '6.00'})
        self.assertContains(res, "marks exceed maximum marks")

        # 3. Test Successful Update
        res = self.client.post(self.url, {'new_marks': '4.50'})
        self.assertContains(res, "Score updated to 4.50")

        # Verify the DB actually updated
        self.response.refresh_from_db()
        self.assertEqual(self.response.marks_given, Decimal('4.50'))

    def test_snooping_student_blocked_from_history(self):
        """Ensure students cannot change the URL ID to view other students' history"""
        # Log in as the snooper, but request the student's ID
        self.client.login(username='snooper', password='password123')
        url = reverse('quiz_history', kwargs={'quiz_id': self.quiz.id, 'user_id': self.student.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class QuestionEngineViewTests(BaseQuizViewTest):
    def setUp(self):
        super().setUp()
        self.client = Client()


        # 3. Create the Attempt
        self.attempt = Attempt.objects.create(quiz=self.quiz, user=self.student)


        self.sa_q = Question.objects.create(question_text="SA", question_type=QuestionType.SHORT_ANSWER)
        self.sa_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.sa_q, order_sequence=1)

        self.mcq_q = Question.objects.create(question_text="MCQ", question_type=QuestionType.MCQ)
        self.mcq_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.mcq_q, order_sequence=2)
        self.mcq_opt = McqOption.objects.create(question=self.mcq_q, option_text="A", is_correct=True)

        self.eo_q = Question.objects.create(question_text="EO", question_type=QuestionType.EITHER_OR)
        self.eo_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.eo_q, order_sequence=3)
        self.eo_opt = EitherOrOption.objects.create(question=self.eo_q, label="True", is_correct=True)

        self.fallback_q = Question.objects.create(question_text="Filler", question_type=QuestionType.TEXT_FILLER)
        self.fallback_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.fallback_q, order_sequence=4)


    def test_access_denied_for_non_students(self):
        """Test that teachers/non-students cannot access the student quiz engine"""
        self.client.login(username='teacher', password='password123')
        url = reverse('question_engine', kwargs={'attempt_id': self.attempt.id, 'question_id': self.sa_qq.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_time_limit_enforcement(self):
        """Test that submitting an answer when time is up returns a 403 Forbidden"""
        self.client.login(username='student', password='password123')

        Attempt.objects.filter(id=self.attempt.id).update(
            start_time=timezone.now() - timedelta(minutes=100)
        )
        self.attempt.refresh_from_db()

        url = reverse('question_engine', kwargs={'attempt_id': self.attempt.id, 'question_id': self.sa_qq.id})
        response = self.client.post(url, {'answer_text': 'Too late!'})

        self.assertContains(
            response,
            "Time is up! Answers can no longer be saved.",
            status_code=403
        )

    # ---- saving answers logic
    def test_post_text_answer(self):
        """Test saving a Short Answer or Essay text response"""
        self.client.login(username='student', password='password123')
        url = reverse('question_engine', kwargs={'attempt_id': self.attempt.id, 'question_id': self.sa_qq.id})

        response = self.client.post(url, {'answer_text': 'My valid answer'})

        self.assertEqual(response.status_code, 200)
        saved_response = Response.objects.get(attempt=self.attempt, quiz_question=self.sa_qq)
        self.assertEqual(saved_response.answer_given, 'My valid answer')

    def test_post_mcq_answer_and_overwrite(self):
        """Test saving an MCQ answer, and ensuring it overwrites older answers correctly"""
        self.client.login(username='student', password='password123')
        url = reverse('question_engine', kwargs={'attempt_id': self.attempt.id, 'question_id': self.mcq_qq.id})

        resp = Response.objects.create(attempt=self.attempt, quiz_question=self.mcq_qq)
        ResponseOption.objects.create(response=resp)  # Blank old option

        response = self.client.post(url, {'mcq_answer': [self.mcq_opt.id]})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ResponseOption.objects.filter(response=resp, mcq_option_id=self.mcq_opt.id).exists())
        self.assertEqual(resp.selected_options.count(), 1)  # Proves the old one was deleted!

    def test_post_eo_answer(self):
        """Test saving an Either/Or answer"""
        self.client.login(username='student', password='password123')
        url = reverse('question_engine', kwargs={'attempt_id': self.attempt.id, 'question_id': self.eo_qq.id})

        response = self.client.post(url, {'eo_answer': self.eo_opt.id})

        self.assertEqual(response.status_code, 200)
        saved_response = Response.objects.get(attempt=self.attempt, quiz_question=self.eo_qq)
        self.assertTrue(ResponseOption.objects.filter(response=saved_response, eo_option_id=self.eo_opt.id).exists())

    # ---------------------------------------------------------
    # 3. GET LOGIC & TEMPLATE ROUTING
    # ---------------------------------------------------------
    def test_get_existing_response_options_extraction(self):
        """Test that a GET request correctly loads previously selected MCQ/EO options into context"""
        self.client.login(username='student', password='password123')
        url = reverse('question_engine', kwargs={'attempt_id': self.attempt.id, 'question_id': self.mcq_qq.id})

        resp = Response.objects.create(attempt=self.attempt, quiz_question=self.mcq_qq)
        ResponseOption.objects.create(response=resp, mcq_option_id=self.mcq_opt.id)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/student_mcq_partial.html')
        self.assertIn(self.mcq_opt.id, response.context['existing_response_option_ids'])

    def test_fallback_template_routing(self):
        """Test that an unmapped question type correctly triggers the 'something went wrong' partial"""
        self.client.login(username='student', password='password123')

        url = reverse('question_engine', kwargs={'attempt_id': self.attempt.id, 'question_id': self.fallback_qq.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/something_went_wrong.html')


class ReviewResponseViewTests(BaseQuizViewTest):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.attempt = Attempt.objects.create(quiz=self.quiz, user=self.student, is_completed=True)


        # --- MCQ ---
        self.mcq_q = Question.objects.create(question_text="MCQ", question_type=QuestionType.MCQ)
        self.mcq_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.mcq_q, order_sequence=1)
        self.mcq_opt = McqOption.objects.create(question=self.mcq_q, maximum_mark=2.00)
        self.mcq_resp = Response.objects.create(attempt=self.attempt, quiz_question=self.mcq_qq)
        ResponseOption.objects.create(response=self.mcq_resp, mcq_option=self.mcq_opt)

        # --- Either/or ---
        self.eo_q = Question.objects.create(question_text="EO", question_type=QuestionType.EITHER_OR)
        self.eo_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.eo_q, order_sequence=2)
        self.eo_opt = EitherOrOption.objects.create(question=self.eo_q, maximum_mark=1.50)
        self.eo_resp = Response.objects.create(attempt=self.attempt, quiz_question=self.eo_qq)
        ResponseOption.objects.create(response=self.eo_resp, eo_option=self.eo_opt)

        # --- Short answer ---
        self.sa_q = Question.objects.create(question_text="SA", question_type=QuestionType.SHORT_ANSWER)
        self.sa_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.sa_q, order_sequence=3)
        ShortAnswerQuestionOption.objects.create(question=self.sa_q, maximum_mark=5.00)
        self.sa_resp = Response.objects.create(attempt=self.attempt, quiz_question=self.sa_qq, answer_given="Test")

        # --- essay ---
        self.essay_q = Question.objects.create(question_text="Essay", question_type=QuestionType.ESSAY_QUESTION)
        self.essay_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.essay_q, order_sequence=4)
        EssayQuestionOption.objects.create(question=self.essay_q, maximum_mark=10.00)
        self.essay_resp = Response.objects.create(attempt=self.attempt, quiz_question=self.essay_qq,
                                                  answer_given="Essay text")

        # --- Unsupported
        self.fallback_q = Question.objects.create(question_text="Fallback", question_type=QuestionType.TEXT_FILLER)
        self.fallback_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.fallback_q, order_sequence=5)
        self.fallback_resp = Response.objects.create(attempt=self.attempt, quiz_question=self.fallback_qq)

    # Test permissions
    def test_snooping_student_blocked(self):
        """Test that a student cannot view another student's attempt"""
        self.client.login(username='snooper', password='password123')
        url = reverse('review_response', kwargs={'attempt_id': self.attempt.id, 'quiz_question_id': self.mcq_qq.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_unenrolled_user_blocked(self):
        """Test that unenrolled staff cannot view the attempt"""
        self.client.login(username='staff', password='password123')
        url = reverse('review_response', kwargs={'attempt_id': self.attempt.id, 'quiz_question_id': self.mcq_qq.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_admin_bypass_allowed(self):
        """Test that admins bypass the enrollment check"""
        self.client.login(username='admin', password='password123')
        url = reverse('review_response', kwargs={'attempt_id': self.attempt.id, 'quiz_question_id': self.mcq_qq.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_response_not_found(self):
        """Test the fallback HTML when a valid user requests a non-existent response"""
        self.client.login(username='student', password='password123')

        fake_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.mcq_q, order_sequence=99)
        url = reverse('review_response', kwargs={'attempt_id': self.attempt.id, 'quiz_question_id': fake_qq.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Response not found.")

    #  Template context
    def test_review_mcq_routing_and_context(self):
        self.client.login(username='student', password='password123')
        url = reverse('review_response', kwargs={'attempt_id': self.attempt.id, 'quiz_question_id': self.mcq_qq.id})

        response = self.client.get(url)
        self.assertTemplateUsed(response, 'partials/review/review_mcq_partial.html')
        self.assertEqual(response.context['question_max_mark'], 2.00)
        self.assertIn(self.mcq_opt.id, response.context['user_selected_option_ids'])

    def test_review_eo_routing_and_context(self):
        self.client.login(username='student', password='password123')
        url = reverse('review_response', kwargs={'attempt_id': self.attempt.id, 'quiz_question_id': self.eo_qq.id})

        response = self.client.get(url)
        self.assertTemplateUsed(response, 'partials/review/review_eo_partial.html')
        self.assertEqual(response.context['question_max_mark'], 1.50)
        self.assertIn(self.eo_opt.id, response.context['user_selected_option_ids'])

    def test_review_sa_routing_and_context(self):
        self.client.login(username='student', password='password123')
        url = reverse('review_response', kwargs={'attempt_id': self.attempt.id, 'quiz_question_id': self.sa_qq.id})

        response = self.client.get(url)
        self.assertTemplateUsed(response, 'partials/review/review_sa_partial.html')
        self.assertEqual(response.context['question_max_mark'], 5.00)

    def test_review_essay_routing_and_context(self):
        self.client.login(username='student', password='password123')
        url = reverse('review_response', kwargs={'attempt_id': self.attempt.id, 'quiz_question_id': self.essay_qq.id})

        response = self.client.get(url)
        self.assertTemplateUsed(response, 'partials/review/review_essay_partial.html')
        self.assertEqual(response.context['question_max_mark'], 10.00)

    def test_review_unsupported_question_type(self):
        """Test the final 'else' branch for unsupported question types"""
        self.client.login(username='student', password='password123')
        url = reverse('review_response',
                      kwargs={'attempt_id': self.attempt.id, 'quiz_question_id': self.fallback_qq.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Question type not supported.")

class QuizTeacherAndListViewTests(BaseQuizViewTest):
    def setUp(self):
        super().setUp()
        self.client = Client()

        self.course = Course.objects.create(name="Computer Science", code="CS101")
        self.course.enrollment.add(self.teacher, self.student)

        self.quiz1 = Quiz.objects.create(course=self.course, name="Midterm Exam", anonymise_student=False)
        self.quiz2 = Quiz.objects.create(course=self.course, name="Final Exam", anonymise_student=True)

    # teacher attempt list
    def test_teacher_student_attempt_list_access(self):
        url = reverse('teacher_student_attempt_list', kwargs={'quiz_id': self.quiz1.id})

        self.client.login(username='teacher2', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(username='teacher', password='password123')
        response = self.client.get(url + "?source=dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/teacher_student_attempt_list.html')
        self.assertEqual(response.context['source'], 'dashboard')

        self.assertIn(self.student, response.context['users'])
        self.assertNotIn(self.snooping_student, response.context['users'])

    # search student
    def test_search_quiz_students_standard(self):
        """Test searching by name or username"""
        self.client.login(username='teacher', password='password123')
        url = reverse('search_quiz_students', kwargs={'quiz_id': self.quiz1.id})

        # Search for student
        response = self.client.get(url, data={'search': 'student'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/teacher/teacher_student_attempt_list_partial.html')
        self.assertIn(self.student, response.context['users'])

        response = self.client.get(url, data={'search': 'xxxYYY'})
        self.assertEqual(response.context['users'].count(), 0)

    def test_search_quiz_students_anonymised(self):
        """Test that if the quiz is anonymised, the search filter is completely ignored"""
        self.client.login(username='teacher', password='password123')
        url = reverse('search_quiz_students', kwargs={'quiz_id': self.quiz2.id})

        response = self.client.get(url, data={'search': 'xxxYYY'})
        self.assertEqual(response.status_code, 200)

        self.assertIn(self.student, response.context['users'])

    # Quiz list
    def test_quiz_list_access(self):
        url = reverse('quiz_list', kwargs={'course_id': self.course.id})

        self.client.login(username='student2', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(username='student', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'all_quiz_list.html')

        self.assertIn(self.quiz1, response.context['quizzes'])
        self.assertIn(self.quiz2, response.context['quizzes'])

    # Search quiz
    def test_search_quiz_queries(self):
        url = reverse('search_quiz', kwargs={'course_id': self.course.id})

        self.client.login(username='teacher2', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(username='teacher', password='password123')
        response = self.client.get(url, data={'search': 'Midterm'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/quiz_record_partial.html')
        self.assertIn(self.quiz1, response.context['quizzes'])
        self.assertNotIn(self.quiz2, response.context['quizzes'])

        response = self.client.get(url, data={'search': str(self.quiz2.id)})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.quiz2, response.context['quizzes'])
        self.assertNotIn(self.quiz1, response.context['quizzes'])