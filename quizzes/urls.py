from django.urls import path
from quizzes import views

urlpatterns = [
    path('create/', views.CreateQuiz.as_view(), name='create-quiz'),
]