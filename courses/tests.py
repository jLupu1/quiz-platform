from django.test import TestCase, Client
from django.urls import reverse

from courses.models import Course
from users.models import User, UserRole


class CourseModelTests(TestCase):
    def setUp(self):
        # 1. Create a test course
        self.course = Course.objects.create(
            code="COM3610",
            name="Advanced Web Development"
        )

        # 2. Create some test users
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

        # Enroll student in course 1 ONLY
        self.course1.enrollment.add(self.student)

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

        # Assuming your url name is 'admin_course_list'
        response = self.client.get(reverse('admin_course_list'))

        # Should redirect them away (to login or dashboard based on your handle_no_permission)
        self.assertEqual(response.status_code, 302)

    def test_admin_course_list_access(self):
        """An admin should be able to access the admin list and see all courses."""
        self.client.login(username='adm', password='password123')

        response = self.client.get(reverse('admin_course_list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['courses']), 2)  # Admins see everything