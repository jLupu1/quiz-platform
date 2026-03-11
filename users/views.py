from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from django.urls import reverse_lazy
from django.views.generic import CreateView

from users.forms import CustomLoginForm, CustomSignupForm


# Create your views here.

class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'

class CustomSignupView(CreateView):
    form_class = CustomSignupForm
    success_url = reverse_lazy("login")
    template_name = 'registration/signup.html'