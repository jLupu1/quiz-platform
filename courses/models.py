from django.db import models

from users.models import User
from django.conf import settings


# Create your models here.
class Course(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    archived = models.BooleanField(default=False)


    # my_user.enrolled_courses.all()
    # my_course.students.all()
    enrollment = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_courses',
        blank=True  # Allows a course to exist with zero students initially
    )
