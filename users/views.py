from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetDoneView, PasswordChangeView, \
    PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, TemplateView

from courses.models import Course
from users.forms import *
from django.contrib.auth import get_user_model

from users.models import UserRole

User = get_user_model()

@login_required(login_url='/users/login')
@user_passes_test(lambda user: user.is_admin)
def admin_user_list(request):
    users = User.objects.all().order_by('last_name', 'first_name')
    context = {
        'users': users
    }
    return render(request, 'manage/admin_user_list.html', context)

@login_required(login_url='/users/login')
@user_passes_test(lambda u: u.is_admin)
def admin_search_user(request):
    users = User.objects.all()
    search = request.GET.get('search', '')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(id__icontains=search)
            # Q(full_name__icontains=search) TODO
        )
    return render(request,"partials/user_record_partial.html",{"users":users})


class UpdateUserView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    context_object_name = 'edited_user'
    template_name = 'manage/admin_manage_user.html'
    success_url = reverse_lazy('admin_user_list')
    form_class = UserUpdateForm

    def test_func(self):
        return self.request.user.role == UserRole.ADMIN

    def handle_no_permission(self):
        return redirect('/users/login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enrolled_courses'] = self.object.enrolled_courses.all()
        return context

@login_required(login_url='/users/login')
@user_passes_test(lambda u: u.is_admin)
@require_POST
def disenroll_user_from_course(request,user_id, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = get_object_or_404(User, id=user_id)

    course.enrollment.remove(user)
    return HttpResponse("")

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile/profile.html'

    def handle_no_permission(self):
        return redirect('/users/login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enrolled_courses'] = self.request.user.enrolled_courses.all()
        return context


class CustomLoginView(UserPassesTestMixin,LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'

    def test_func(self):
        return not self.request.user.is_authenticated
    def get_success_url(self):
        user = self.request.user

        if user.is_admin:
            return reverse_lazy('admin_course_list')

        return reverse_lazy('courses')


class CustomSignupView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = CustomSignupForm
    success_url = reverse_lazy("signup")
    template_name = 'registration/signup.html'

    def test_func(self):
        return self.request.user.role == UserRole.ADMIN

    def handle_no_permission(self):
        return redirect('/')

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'registration/custom_password_reset_form.html'
    success_url = reverse_lazy("password_reset_done")

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/custom_password_reset_done.html'

class CustomPasswordSetView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'registration/custom_reset_set_password.html'
    success_url = reverse_lazy("password_reset_complete")

class CustomPasswordChangeDoneView(PasswordResetCompleteView):
    template_name = 'registration/custom_password_reset_complete.html'

class CustomPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'registration/custom_password_change_form.html'
    success_url = reverse_lazy('profile')
    success_message = "Your password was successfully updated!"



# Error views
def error_401(request, exception):
    context = {
        'status_code': 401,
        'error_title': 'Permission Denied',
        'error_message': "Sorry, you don't seem to be authenticated.",
        'exception': str(exception) if exception else ''
    }
    return render(request, 'errors/error_page.html', status=401, context=context)
def error_403(request, exception):
    context = {
        'status_code': 403,
        'error_title': 'Access Denied',
        'error_message': "Sorry, you don't have permission to view this page.",
        'exception': str(exception) if exception else ''
    }
    return render(request, 'errors/error_page.html', status=403,
                  context=context)

def error_404(request, exception):
    context = {
        'status_code': 404,
        'error_title': 'Page Not Found',
        'error_message': "Sorry, we could not find this page.",
        'exception': str(exception) if exception else ''
    }
    return render(request, 'errors/error_page.html', status=404, context=context)

def error_405(request, exception):
    context = {
        'status_code': 405,
        'error_title': 'Method Not Allowed',
        'error_message': "Sorry, this action is not allowed.",
        'exception': str(exception) if exception else ''
    }
    return render(request, 'errors/error_page.html', status=405, context=context)

def error_500(request):
        context = {
            'status_code': 500,
            'error_title': 'Server Error',
            'error_message': "Sorry, something went wrong.",
        }
        return render(request, 'errors/error_page.html', status=500, context=context)



