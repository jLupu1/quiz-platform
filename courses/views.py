from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from courses.forms import CourseCreationForm
from courses.models import Course
from users.models import UserRole
from users.views import error_403


# Create your views here.
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


@login_required(login_url='/users/login')
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)

    is_admin = request.user.is_admin
    is_enrolled = course.enrollment.filter(id=request.user.id).exists()

    if not(is_admin or is_enrolled):
        return error_403(request, exception="You are not enrolled in this module/course")

    context = {
        'course': course,
        'default_students': course.enrollment.filter(role=UserRole.STUDENT)  # Add this!
    }
    # context will need course detail and quizzes
    if request.user.is_teacher or request.user.is_admin:
        return render(request, 'courses/course_detail_teacher.html', context)
    else:
        return render(request, 'courses/course_detail_student.html', context)

@login_required(login_url='/users/login')
def search_course_students(request,pk):
    # returns 404 if not found
    course = get_object_or_404(Course, pk=pk)
    search_text = request.GET.get('search', '')

    students = course.enrollment.filter(role=UserRole.STUDENT)

    # Filters out based on what I searched for in the text box
    if search_text:
        students = students.filter(
            Q(first_name__icontains=search_text) |
            Q(last_name__icontains=search_text) |
            Q(username__icontains=search_text)
        )
    return render(request, 'partials/student_list_partial.html', {'students': students})

# Admin page to see a complete list of courses
@login_required(login_url='/users/login')
@user_passes_test(lambda user: user.is_admin)
def admin_course_list(request):
    courses = Course.objects.all()
    context = {
        'courses': courses
    }
    return render(request, 'courses/admin_courses_list.html', context)



