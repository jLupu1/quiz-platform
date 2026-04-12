from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, UpdateView
from courses.forms import CourseCreationForm
from courses.models import Course
from users.models import UserRole


# Create your views here.
@login_required(login_url='/users/login')
def home_router(request):
    if request.user.is_admin:
        return redirect('admin_course_list')
    else:
        return redirect('courses')
class CoursesView(LoginRequiredMixin, ListView):
    model = Course
    context_object_name = 'courses'
    template_name = 'courses/courses.html'

    def get_queryset(self):
        return self.request.user.enrolled_courses.all()
    def handle_no_permission(self):
        return redirect('/users/login')

class CourseCreateView(LoginRequiredMixin,UserPassesTestMixin, CreateView):
    model = Course
    form_class = CourseCreationForm
    template_name = 'manage/create_update_course.html'
    success_url = reverse_lazy('admin_course_list')

    def handle_no_permission(self):
        return redirect('/users/login')

    # Only let them see this page if they are logged in AND are a admin
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_admin


@login_required(login_url='/users/login')
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    teachers = course.enrollment.filter(role=UserRole.TEACHER,is_active=True)

    is_admin = request.user.is_admin
    is_enrolled = course.enrollment.filter(id=request.user.id).exists()

    all_quizzes = course.quiz_set.all()

    # gets active and upcoming quizzes.
    active_quizzes = [quiz for quiz in all_quizzes if quiz.is_currently_available
                      or (quiz.open_date and quiz.open_date > timezone.now())]
    closed_quizzes = [quiz for quiz in all_quizzes if not quiz.is_currently_available]

    active_quizzes = sorted(active_quizzes, key=lambda q: q.close_date or timezone.now())

    if not(is_admin or is_enrolled):
        raise PermissionDenied("You are not enrolled in this module/course")

    context = {
        'course': course,
        'default_students': course.enrollment.filter(role=UserRole.STUDENT,is_active=True),
        'upcoming_quizzes': active_quizzes,
        'closed_quizzes': closed_quizzes,
        'teachers': teachers,
    }
    # context will need course detail and quizzes
    if request.user.is_teacher or request.user.is_admin:
        return render(request, 'courses/course_detail_teacher.html', context)
    else:
        return render(request, 'courses/course_detail_student.html', context)

@login_required(login_url='/users/login')
@user_passes_test(lambda user: user.is_staff_member)
def search_course_students(request,pk):
    # returns 404 if not found
    course = get_object_or_404(Course, pk=pk)
    search_text = request.GET.get('search', '')

    students = course.enrollment.filter(role=UserRole.STUDENT,is_active=True)

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
    return render(request, 'manage/admin_courses_list.html', context)

def search_courses(request):
    courses = Course.objects.all()
    search_text = request.GET.get('search', '')
    if search_text:
        courses = courses.filter(
            Q(code__icontains=search_text) |
            Q(name__icontains=search_text)
        )
    return render(request, 'partials/course_record_partial.html',{'courses': courses})


class CourseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Course
    form_class = CourseCreationForm
    template_name = 'manage/create_update_course.html'  # Point this to your edit template
    success_url = reverse_lazy('admin_course_list')  # Where to go after saving

    def test_func(self):
        return self.request.user.role == UserRole.ADMIN