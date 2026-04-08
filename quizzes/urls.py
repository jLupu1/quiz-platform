from django.urls import path
from quizzes import views

urlpatterns = [
    path('create/<int:course_id>/', views.CreateQuiz.as_view(), name='create-quiz'),
    path('edit/<int:pk>/',views.EditQuiz.as_view(), name='edit-quiz'),
    path('delete/<int:pk>/',views.delete_quiz, name='delete_quiz'),
    path('quiz/<int:quiz_id>/info/', views.quiz_landing_page, name='quiz_landing'),
    path('attempt/<int:attempt_id>/take/', views.StudentTakeQuiz.as_view(), name='take_quiz'),
    path('attempt/<attempt_id>/question/<question_id>/',views.question_engine,name='question_engine'),
    path('attempt/<int:attempt_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('attempt/<int:attempt_id>/results/', views.quiz_results, name='quiz_results'),
]