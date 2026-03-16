from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetDoneView, PasswordChangeView, \
    PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView, TemplateView
from users.forms import *
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomLoginView(UserPassesTestMixin,LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'

    def test_func(self):
        return not self.request.user.is_authenticated


class CustomSignupView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = CustomSignupForm
    success_url = reverse_lazy("signup")
    template_name = 'registration/signup.html'

    def test_func(self):
        print(self.request.user.role)
        return self.request.user.role == 2

    def handle_no_permission(self):
        return redirect('/')

# Error views
def error_403(request, exception):
    return render(request, 'errors/error_403.html', status=403)

def error_404(request, exception):
    return render(request, 'errors/error_404.html', status=404)

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile/profile.html'

    def handle_no_permission(self):
        return redirect('/users/login')

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