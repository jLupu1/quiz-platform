from django.contrib import admin
from django.urls import path
from courses import views

urlpatterns = [
    path('create/',views.CourseCreateView.as_view(),name='create_course'),
    path('',views.CoursesView.as_view(),name='courses'),
]