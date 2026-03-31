from django.urls import path
from quizzes import views

urlpatterns = [
    path('create/<int:course_id>', views.CreateQuiz.as_view(), name='create-quiz'),
    path('edit/<int:pk>/',views.EditQuiz.as_view(), name='edit-quiz'),
]