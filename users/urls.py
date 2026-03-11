from django.contrib import admin
from django.urls import path
from users import views

urlpatterns = [
    path("signup", views.CustomSignupView.as_view(), name="signup"),
    path("my-profile",views.ProfileView.as_view(), name="profile"),
]