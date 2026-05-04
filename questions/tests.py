from django.test import TestCase, Client, RequestFactory
from decimal import Decimal

from django.urls import reverse

from courses.models import Course
from questions.models import (
    Question, QuestionType, McqOption, EitherOrOption,
    ShortAnswerQuestionOption, EssayQuestionOption
)
from questions.views import get_either_or_partial
from quizzes.models import Quiz, QuizQuestion
from users.models import User, UserRole


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


class QuestionsViewsCoverageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        self.admin = User.objects.create_user(
            username='admin_user', password='password123', role=UserRole.ADMIN,email='admin@email.com'
        )
        self.enrolled_staff = User.objects.create_user(
            username='staff_enrolled', password='password123', role=UserRole.TEACHER, email='tchr1@email.com'
        )
        self.unenrolled_staff = User.objects.create_user(
            username='staff_unenrolled', password='password123',role=UserRole.TEACHER,email='tchr2@email.com'
        )
        self.student = User.objects.create_user(
            username='student', password='password123', role=UserRole.STUDENT,email='stud@email.com'
        )

        self.course = Course.objects.create(name="Software Engineering", code="COM3610")
        self.course.enrollment.add(self.enrolled_staff, self.student)
        self.quiz = Quiz.objects.create(name="Midterm", course=self.course)

        # 3. Setup Initial Questions for Edit/Delete Tests
        self.mcq_q = Question.objects.create(question_text="Q1", question_type=0)
        self.mcq_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.mcq_q, order_sequence=1)
        McqOption.objects.create(question=self.mcq_q, option_text="A", is_correct=True)

        self.eo_q = Question.objects.create(question_text="Q2", question_type=1)
        self.eo_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.eo_q, order_sequence=2)

        self.sa_q = Question.objects.create(question_text="Q3", question_type=2)
        self.sa_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.sa_q, order_sequence=3)
        ShortAnswerQuestionOption.objects.create(question=self.sa_q, answer_text="Model", required_words=['test'])

        self.essay_q = Question.objects.create(question_text="Q4", question_type=3)
        self.essay_qq = QuizQuestion.objects.create(quiz=self.quiz, question=self.essay_q, order_sequence=4)
        EssayQuestionOption.objects.create(question=self.essay_q)

        # URLs
        self.create_url = reverse('create_question', kwargs={'quiz_id': self.quiz.id})
        self.view_url = reverse('view_questions', kwargs={'quiz_id': self.quiz.id})
        self.bank_url = reverse('question_bank', kwargs={'course_id': self.course.id})
        self.search_url = reverse('search_questions', kwargs={'course_id': self.course.id})


    # Create questions tests

    def test_create_question_access_permissions(self):
        """Test that only enrolled staff/admins can access the create view"""
        # Unauthenticated
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 302)

        # Unenrolled Staff-403
        self.client.login(username='staff_unenrolled', password='password123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 403)

        # Enrolled Staff-200
        self.client.login(username='staff_enrolled', password='password123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

    def test_create_mcq_success(self):
        self.client.login(username='admin_user', password='password123')
        data = {
            'question_type': '0', 'question_text': 'What is Python?',
            'mcq_option_text': ['Language', 'Snake'], 'mcq_max_mark': ['1', '0'],
            'mcq_negative_mark': ['0', '0'], 'mcq_option_feedback': ['Yes', 'No'],
            'mcq_is_correct_list': ['True', 'False'], 'mcq_isMultipleAnswer': 'on'
        }
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Question.objects.filter(question_text='What is Python?').exists())

    def test_create_mcq_validation_errors(self):
        self.client.login(username='admin_user', password='password123')
        # Less than 2 options
        data = {'question_type': '0', 'question_text': 'Test', 'mcq_option_text': ['Only One']}
        response = self.client.post(self.create_url, data)
        self.assertFormError(response.context['form'], None, 'Multiple Choice questions require at least two options.')

        # Blank option
        data['mcq_option_text'] = ['Valid', '   ']
        response = self.client.post(self.create_url, data)
        self.assertFormError(response.context['form'], None,
                             'All Multiple Choice options must contain text. Blank options are not allowed.')

    def test_create_eo_success_and_validation(self):
        self.client.login(username='admin_user', password='password123')
        # Invalid - three options
        data = {'question_type': '1', 'question_text': 'True or False?', 'eo_label_text': ['True']}
        response = self.client.post(self.create_url, data)
        self.assertFormError(response.context['form'], None,
                             'Either/Or questions must have exactly two options (e.g., True and False).')

        data = {
            'question_type': '1', 'question_text': 'True or False?',
            'eo_label_text': ['True', 'False'], 'eo_is_correct_list': ['True', 'False'],
            'eo_specific_feedback': ['', ''], 'eo_max_mark': ['1', '0'], 'eo_negative_mark': ['0', '0']
        }
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, 302)

    def test_create_sa_success_and_validation(self):
        self.client.login(username='admin_user', password='password123')
        # Invalid - no model answer
        data = {'question_type': '2', 'question_text': 'Define API', 'sa_answer': '   '}
        response = self.client.post(self.create_url, data)
        self.assertFormError(response.context['form'], None,
                             'You must provide an Acceptable / Model Answer for Short Answer questions.')

        # Success
        data['sa_answer'] = 'Application Programming Interface'
        data['sa_required_keywords'] = 'application, interface'
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, 302)

    def test_create_essay_success(self):
        self.client.login(username='admin_user', password='password123')
        # Essay
        data = {'question_type': '3', 'question_text': 'Write an essay.', 'essay_model_answer': 'Model'}
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, 302)



    def test_create_invalid_question_type(self):
        """Test that submitting a question type outside the choices fails form validation"""
        self.client.login(username='admin_user', password='password123')

        data = {'question_type': '99', 'question_text': 'Bad Type'}
        response = self.client.post(self.create_url, data)

        self.assertEqual(response.status_code, 200)

        self.assertFormError(
            response.context['form'],
            'question_type',
            'Select a valid choice. 99 is not one of the available choices.'
        )


    #    ---- Partials -----
    def test_get_question_partials(self):
        self.client.login(username='admin_user', password='password123')
        url = reverse('get_question_partial')

        # Test all types 0-4
        for q_type in ['0', '1', '2', '3', '4']:
            response = self.client.get(f"{url}?question_type={q_type}")
            self.assertEqual(response.status_code, 200)

        # Test invalid
        response = self.client.get(f"{url}?question_type=99")
        self.assertEqual(response.content, b"")

    def test_add_mcq_options(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('add_mcq_options'))
        self.assertEqual(response.status_code, 200)

    def test_get_either_or_partial_direct(self):
        request = self.factory.get('/dummy-url/')
        request.user = self.enrolled_staff
        response = get_either_or_partial(request)
        self.assertEqual(response.status_code, 200)


    # ---- Edit and Delete ----
    def test_edit_question_get_contexts(self):
        self.client.login(username='admin_user', password='password123')

        # Test MCQ Context
        response = self.client.get(reverse('edit_question', kwargs={'pk': self.mcq_qq.id}))
        self.assertIn('mcq_options', response.context)

        # Test SA Context
        response = self.client.get(reverse('edit_question', kwargs={'pk': self.sa_qq.id}))
        self.assertIn('sa_options', response.context)
        self.assertEqual(response.context['words_display'], 'test')

    def test_edit_question_post_updates(self):
        self.client.login(username='admin_user', password='password123')

        # Update Essay with rubric deletion trigger
        data = {'question_type': '3', 'question_text': 'Updated Essay', 'clear_essay_rubric': 'on'}
        response = self.client.post(reverse('edit_question', kwargs={'pk': self.essay_qq.id}), data)
        self.assertEqual(response.status_code, 302)

    def test_delete_question(self):
        self.client.login(username='admin_user', password='password123')
        url = reverse('delete_question', kwargs={'pk': self.mcq_qq.id})

        # GET should fail
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(QuizQuestion.objects.filter(id=self.mcq_qq.id).exists())


    def test_view_questions(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(self.view_url)
        self.assertEqual(response.status_code, 200)

    def test_question_bank_and_search(self):
        self.client.login(username='admin_user', password='password123')

        response = self.client.get(self.bank_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.search_url, data={'search': 'Q1'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.mcq_qq, response.context['questions'])