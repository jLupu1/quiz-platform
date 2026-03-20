from django.urls import path
from dashboard import views

urlpatterns = [
    path('',views.index_dashboard,name='index'),
    path('student/',views.student_dashboard,name='student_dashboard'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),

]