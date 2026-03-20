from django.contrib.auth.models import AbstractUser
from django.db import models
from enum import IntEnum

# UserRole enum to assign student what access they have
class UserRole(IntEnum):
    STUDENT = 0
    TEACHER = 1
    ADMIN = 2

    @classmethod
    def choices(cls):
        return [(cls.value,cls.name) for cls in UserRole]
class Arrangement(models.Model):
    extra_time = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    rest_breaks = models.IntegerField(null=True, blank=True)
    special_equipment = models.CharField(max_length=500, null=True, blank=True)

class User(AbstractUser):
    role = models.IntegerField(choices=UserRole.choices(), default=UserRole.STUDENT)

    user_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField('email', unique=True)

    arrangement = models.OneToOneField(Arrangement, on_delete=models.SET_NULL, null=True, blank=True)

    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_teacher(self):
        return self.role == UserRole.TEACHER

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_staff_member(self):
        return self.role in [UserRole.TEACHER, UserRole.ADMIN]

    def __str__(self):
        return self.first_name + " " + self.last_name + " (" + self.username + ")"



