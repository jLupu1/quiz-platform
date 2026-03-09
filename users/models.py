from django.contrib.auth.models import AbstractUser
from django.db import models
from utils.user_roles import UserRole

# Create your models here.

class Arrangement(models.Model):
    extra_time = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    rest_breaks = models.IntegerField(null=True, blank=True)
    special_equipment = models.CharField(max_length=500, null=True, blank=True)

class User(AbstractUser):
    role = models.IntegerField(choices=UserRole.choices(), default=UserRole.STUDENT)

    user_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True) #TODO need to implement upload directory

    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField('email', unique=True)

    #TODO implement arrangement foreign key
    arrangement = models.ForeignKey('Arrangement', on_delete=models.CASCADE, null=True, blank=True)

    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']



