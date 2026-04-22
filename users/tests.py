from django.test import TestCase
from users.models import User, UserRole, Arrangement

class UserModelTests(TestCase):
    def setUp(self):
        # Set up our test users
        self.student = User.objects.create(
            username='student1', email='student@test.com', role=UserRole.STUDENT
        )
        self.teacher = User.objects.create(
            username='teacher1', email='teacher@test.com', role=UserRole.TEACHER
        )
        self.admin = User.objects.create(
            username='admin1', email='admin@test.com', role=UserRole.ADMIN
        )

    def test_user_role_properties(self):
        """Test the boolean properties for user roles."""
        self.assertTrue(self.student.is_student)
        self.assertFalse(self.student.is_staff_member)

        self.assertTrue(self.teacher.is_teacher)
        self.assertTrue(self.teacher.is_staff_member)

        self.assertTrue(self.admin.is_admin)
        self.assertTrue(self.admin.is_staff_member)

    def test_arrangement_creation(self):
        """Test that an arrangement can be created and linked to a user."""
        arrangement = Arrangement.objects.create(
            extra_time=25.00,
            rest_breaks=True
        )
        self.student.arrangement = arrangement
        self.student.save()

        self.assertEqual(self.student.arrangement.extra_time, 25.00)
        self.assertTrue(self.student.arrangement.rest_breaks)