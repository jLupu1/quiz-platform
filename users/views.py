from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.template import loader
from django.urls import reverse_lazy
from django.views.generic import CreateView

from users.forms import CustomLoginForm, CustomSignupForm


class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'

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