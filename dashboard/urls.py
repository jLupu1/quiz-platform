from django.urls import path
from dashboard import views

urlpatterns = [
    path('',views.index_dashboard,name='index'),
    path('student/',views.student_dashboard,name='student_dashboard'),
]