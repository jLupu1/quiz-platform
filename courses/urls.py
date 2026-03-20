from django.contrib import admin
from django.urls import path
from courses import views

urlpatterns = [
    path('detail/<int:pk>', views.course_detail, name='course_detail'),
    path('create/',views.CourseCreateView.as_view(),name='create_course'),
    path('',views.CoursesView.as_view(),name='courses'),
    path('detail/<int:pk>/search-students/', views.search_course_students, name='search_course_students'),
]