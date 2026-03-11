from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView, TemplateView
from users.forms import CustomLoginForm, CustomSignupForm
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomLoginView(UserPassesTestMixin,LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'

    def test_func(self):
        return not self.request.user.is_authenticated


class CustomSignupView(LoginRequiredMixin, UserPassesTestMixin,CreateView):
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
    # model = User
    template_name = 'profile/profile.html'
    # context_object_name = 'user_profile'