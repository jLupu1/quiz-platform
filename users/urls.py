from django.contrib import admin
from django.urls import path
from users import views

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),

    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/done/', views.CustomPasswordChangeDoneView.as_view(), name='password_reset_complete'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordSetView.as_view(), name='password_reset_confirm'),
    path("signup", views.CustomSignupView.as_view(), name="signup"),
    path("my-profile",views.ProfileView.as_view(), name="profile"),
]