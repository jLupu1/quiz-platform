from django.contrib import admin
from django.urls import path
from users import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('password_change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/done/', views.CustomPasswordChangeDoneView.as_view(), name='password_reset_complete'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordSetView.as_view(), name='password_reset_confirm'),
    path("signup", views.CustomSignupView.as_view(), name="signup"),


    # profile URL
    path("my-profile",views.ProfileView.as_view(), name="profile"),


    # Admin Manage URLs
    path('manage/',views.admin_user_list,name='admin_user_list'),
    path('manage/search-user', views.admin_search_user, name='search_user'),
    path('manage/<int:pk>',views.UpdateUserView.as_view(),name='admin_manage_user'),
    path('manage/<int:user_id>/remove-course/<int:course_id>/', views.disenroll_user_from_course, name='disenroll_user'),

]