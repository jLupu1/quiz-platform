from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from courses.forms import CourseCreationForm
from courses.models import Course


# Create your views here.
# @login_required(login_url='login')
def index(request):
    if request.user.is_authenticated:
        return HttpResponse("Index Page")
    else:
        return redirect('users/login')

class CoursesView(LoginRequiredMixin, ListView):
    model = Course
    context_object_name = 'courses'
    template_name = 'courses/courses.html'

    def get_queryset(self):
        print(self.request.user.enrolled_courses.all())
        return self.request.user.enrolled_courses.all()
    def handle_no_permission(self):
        return redirect('/users/login')

class CourseCreateView(LoginRequiredMixin,UserPassesTestMixin, CreateView):
    model = Course
    form_class = CourseCreationForm
    template_name = 'manage/create_course.html'
    success_url = reverse_lazy('profile')

    def handle_no_permission(self):
        return redirect('/users/login')

    # Only let them see this page if they are logged in AND are a teacher/admin
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_teacher or user.is_admin)