from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from courses.models import Course
from questions.models import Question
from quizzes.models import Quiz, QuizQuestion
from users.models import User, UserRole

class CourseModelTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(
            code="COM3610",
            name="Advanced Web Development"
        )
        self.student1 = User.objects.create(username="student1", email="s1@test.com", role=UserRole.STUDENT)
        self.student2 = User.objects.create(username="student2", email="s2@test.com", role=UserRole.STUDENT)

    def test_course_creation_defaults(self):
        """Test that a course is created correctly and defaults to unarchived."""
        self.assertEqual(self.course.code, "COM3610")
        self.assertEqual(self.course.name, "Advanced Web Development")
        self.assertFalse(self.course.archived)  # Should default to False

    def test_course_enrollment(self):
        """Test adding students to the ManyToMany enrollment field."""
        # Enroll the students
        self.course.enrollment.add(self.student1, self.student2)

        # Check the course perspective
        self.assertEqual(self.course.enrollment.count(), 2)
        self.assertIn(self.student1, self.course.enrollment.all())

        # Check the reverse relationship (User perspective)
        self.assertEqual(self.student1.enrolled_courses.count(), 1)
        self.assertEqual(self.student1.enrolled_courses.first(), self.course)


class CourseViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Users
        self.student = User.objects.create_user(username='stu', password='password123',email='stu@email.com' ,role=UserRole.STUDENT)
        self.admin = User.objects.create_user(username='adm', password='password123', email='adm@email.com' ,role=UserRole.ADMIN)

        # Create Courses
        self.course1 = Course.objects.create(code="CS101", name="Intro")
        self.course2 = Course.objects.create(code="CS202", name="Advanced")
        self.course3 = Course.objects.create(code="COM1003", name="Java")

        # Enroll student in course 1 ONLY
        self.course1.enrollment.add(self.student)

        self.no_access_url = 'users/login/'
        self.course_search_url = reverse('search_course')

    def test_student_course_list_access(self):
        """A student should only see courses they are enrolled in."""
        self.client.login(username='stu', password='password123')

        # Assuming your url name is 'courses'
        response = self.client.get(reverse('courses'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/courses.html')

        # Check that only course 1 is in the context
        courses_in_context = response.context['courses']
        self.assertIn(self.course1, courses_in_context)
        self.assertNotIn(self.course2, courses_in_context)

    def test_student_blocked_from_admin(self):
        """A student should get a 302 Redirect if they try to view the admin list."""
        self.client.login(username='stu', password='password123')

        response = self.client.get(reverse('admin_course_list'))

        # Should redirect them away
        self.assertEqual(response.status_code, 302)

    def test_admin_course_list_access(self):
        """An admin should be able to access the admin list and see all courses."""
        self.client.login(username='adm', password='password123')

        response = self.client.get(reverse('admin_course_list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['courses']), 3)  # Admins see everything

    def test_unauthorised_access_to_create_course(self):
        self.client.login(username='stu', password='password123')

        response = self.client.get(reverse('create_course'))
        self.assertEqual(response.status_code, 403)

    def test_unauthorised_access_to_view_courses(self):
        response = self.client.get(reverse('courses'))
        self.assertEqual(response.status_code, 403)

    def test_unauthorised_student_access_to_manage_courses(self):
        self.client.login(username='stu', password='password123')
        response = self.client.get(reverse('course_update', kwargs={'pk': self.course1.pk}))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_access_to_manage_courses(self):
        response = self.client.get(reverse('course_update', kwargs={'pk': self.course1.pk}))
        expected_url = f"/users/login/?next=/courses/manage/{str(self.course1.pk)}"
        self.assertRedirects(response,expected_url)

    def test_search_courses_admin_no_search(self):
        """Test that an admin sees all courses when search is empty"""
        self.client.login(username='adm', password='password123')

        response = self.client.get(self.course_search_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/course_record_partial.html')

        courses_in_context = response.context['courses']
        self.assertEqual(courses_in_context.count(), 3)

    def test_search_courses_admin_with_search(self):
        """Test that the Q-object filter correctly searches names and codes"""
        self.client.login(username='adm', password='password123')

        response = self.client.get(self.course_search_url, data={'search': 'COM'})

        self.assertEqual(response.status_code, 200)

        courses_in_context = response.context['courses']

        self.assertEqual(courses_in_context.count(), 1)
        self.assertNotIn(self.course1, courses_in_context)
        self.assertNotIn(self.course2, courses_in_context)
        self.assertIn(self.course3, courses_in_context)



class TestIndexRouting(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('index')

        self.student = User.objects.create_user(username='stu', password='password123', email='stu@email.com',
                                                role=UserRole.STUDENT)
        self.admin = User.objects.create_user(username='adm', password='password123', email='adm@email.com',
                                              role=UserRole.ADMIN, is_staff=True)

    def test_routing_unauthenticated(self):
        """An unauthenticated user should be redirected to login page."""
        response = self.client.get(self.url)
        expected_url = f"/users/login/?next={self.url}"
        self.assertRedirects(response, expected_url)

    def test_routing_authenticated_admin(self):
        self.client.login(username=self.admin.username, password='password123')
        response = self.client.get(self.url)
        expected_url = f"/courses/manage/"
        self.assertRedirects(response, expected_url)

    def test_routing_authenticated_student(self):
        self.client.login(username=self.student.username, password='password123')
        response = self.client.get(self.url)
        expected_url = f"/courses/"
        self.assertRedirects(response, expected_url)


class SearchCourseStudentsViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff_user@email.com',
            password='password123',
            role=UserRole.ADMIN
        )

        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular_user@email.com',
            password='password123',
            role=UserRole.STUDENT
        )

        self.course = Course.objects.create(name="Advanced Python", code="COM300")

        self.url = reverse('search_course_students', kwargs={'pk': self.course.pk})

        self.student1 = User.objects.create_user(
            username='alice_j', first_name='Alice', last_name='Jones', email='alice_j@email.com',
            password='password123', is_active=True, role=UserRole.STUDENT  # Adjust role assignment to match your model
        )
        self.student2 = User.objects.create_user(
            username='bob_s', first_name='Bob', last_name='Smith',email='bob_s.@email.com',
            password='password123', is_active=True, role=UserRole.STUDENT
        )
        self.inactive_student = User.objects.create_user(
            username='charlie_b', first_name='Charlie', last_name='Brown', email='charlie_b@email.com',
            password='password123', is_active=False, role=UserRole.STUDENT
        )

        self.course.enrollment.add(self.student1, self.student2, self.inactive_student)

    def test_search_course_students_regular_user_denied(self):
        """Test that regular users without staff privileges are blocked"""
        self.client.login(username='regular_user', password='password123')
        response = self.client.get(self.url)

        expected_url = f"/users/login/?next={self.url}"
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    def test_search_course_students_404_not_found(self):
        """Test that passing an invalid PK returns a 404 page"""
        self.client.login(username='staff_user', password='password123')

        # fake pk
        bad_url = reverse('search_course_students', kwargs={'pk': 9999})
        response = self.client.get(bad_url)

        # Assert 404 error
        self.assertEqual(response.status_code, 404)

    def test_search_course_students_no_search_text(self):
        """Test that the view returns all ACTIVE students in the course when search is empty"""
        self.client.login(username='staff_user', password='password123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/student_list_partial.html')

        students_in_context = response.context['students']

        # Should contain Alice and Bob, but not Charlie as inactive
        self.assertEqual(students_in_context.count(), 2)
        self.assertIn(self.student1, students_in_context)
        self.assertIn(self.student2, students_in_context)
        self.assertNotIn(self.inactive_student, students_in_context)

    def test_search_course_students_with_search_text(self):
        """Test that the Q objects correctly filter by name/username"""
        self.client.login(username='staff_user', password='password123')

        # Search for alice
        response = self.client.get(self.url, data={'search': 'alice'})

        students_in_context = response.context['students']

        self.assertEqual(response.status_code, 200)
        # only contain alice
        self.assertEqual(students_in_context.count(), 1)
        self.assertIn(self.student1, students_in_context)
        self.assertNotIn(self.student2, students_in_context)


class CourseDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin_user', password='password123', role=UserRole.ADMIN, email='admin@email.com'
        )
        self.teacher = User.objects.create_user(
            username='teacher_user', password='password123', role=UserRole.TEACHER, email='teacher@email.com'
        )
        self.enrolled_student = User.objects.create_user(
            username='student1', password='password123', role=UserRole.STUDENT, email='stud1@email.com'
        )
        self.unenrolled_student = User.objects.create_user(
            username='student2', password='password123', role=UserRole.STUDENT, email='stud2@email.com'
        )

        self.course = Course.objects.create(name="Software Engineering", code="COM3610")
        self.course.enrollment.add(self.teacher, self.enrolled_student)

        self.url = reverse('course_detail', kwargs={'pk': self.course.pk})

        now = timezone.now()

        test_question = Question.objects.create(
            question_text="Test Question", question_type=1)



        # Setup mock quizzes (adjust parameters to match your model exactly)
        self.active_quiz = Quiz.objects.create(
            course=self.course, name="Active Quiz",
            open_date=now - timedelta(days=1), close_date=now + timedelta(days=1),
            status=Quiz.QuizStatus.OPEN
        )
        self.upcoming_quiz = Quiz.objects.create(
            course=self.course, name="Upcoming Quiz",
            open_date=now + timedelta(days=2), close_date=now + timedelta(days=3),
            status=Quiz.QuizStatus.SCHEDULED
        )
        self.closed_quiz = Quiz.objects.create(
            course=self.course, name="Closed Quiz",
            open_date=now - timedelta(days=5), close_date=now - timedelta(days=4),
            status = Quiz.QuizStatus.CLOSED
            # 'is_currently_available' should be False
        )

        QuizQuestion.objects.create(
            question=test_question,
            quiz=self.active_quiz,
            order_sequence=1,
        )
        QuizQuestion.objects.create(
            question=test_question,
            quiz=self.upcoming_quiz,
            order_sequence=1,

        )
        QuizQuestion.objects.create(
            question=test_question,
            quiz=self.closed_quiz,
            order_sequence=1,

        )

    def test_course_detail_unauthenticated(self):
        """Test anonymous users are redirected to login"""
        response = self.client.get(self.url)
        expected_url = f"/users/login/?next={self.url}"
        self.assertRedirects(response, expected_url)

    def test_course_detail_404_not_found(self):
        """Test accessing a non-existent course PK returns 404"""
        self.client.login(username='admin_user', password='password123')
        bad_url = reverse('course_detail', kwargs={'pk': 9999})
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 404)

    def test_course_detail_unenrolled_student_denied(self):
        """Test that a student who isn't enrolled gets a PermissionDenied (403)"""
        self.client.login(username='student2', password='password123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_course_detail_admin_access(self):
        """Test that an admin can access the course even if not explicitly enrolled"""
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/course_detail_teacher.html')

    def test_course_detail_teacher_access(self):
        """Test that an enrolled teacher gets the teacher template"""
        self.client.login(username='teacher_user', password='password123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/course_detail_teacher.html')

        self.assertIn(self.teacher, response.context['teachers'])

    def test_course_detail_student_access_and_quizzes(self):
        """Test student gets student template and quizzes are correctly filtered"""
        self.client.login(username='student1', password='password123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/course_detail_student.html')

        context = response.context

        self.assertIn(self.enrolled_student, context['default_students'])

        upcoming = context['upcoming_quizzes']
        closed = context['closed_quizzes']

        self.assertIn(self.closed_quiz, closed)
        self.assertNotIn(self.active_quiz, closed)

        if len(upcoming) >= 2:
            self.assertEqual(upcoming[0], self.active_quiz)
            self.assertEqual(upcoming[1], self.upcoming_quiz)