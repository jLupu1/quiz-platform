from os import pathconf_names

from django.urls import path
from quizzes import views

urlpatterns = [
    path('create/<int:course_id>/', views.CreateQuiz.as_view(), name='create-quiz'),
    path('edit/<int:pk>/',views.EditQuiz.as_view(), name='edit-quiz'),
    path('delete/<int:pk>/',views.delete_quiz, name='delete_quiz'),

    # Take quiz
    path('quiz/<int:quiz_id>/info/', views.quiz_landing_page, name='quiz_landing'),
    path('/quiz/<int:quiz_id>/password/',views.password_checker,name='quiz_password_prompt'),
    path('attempt/<int:attempt_id>/take/', views.StudentTakeQuiz.as_view(), name='take_quiz'),
    path('attempt/<attempt_id>/question/<question_id>/',views.question_engine,name='question_engine'),
    path('attempt/<int:attempt_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('attempt/<int:attempt_id>/results/', views.quiz_results, name='quiz_results'),

    # Review Quiz
    path('quiz/<int:quiz_id>/history/<int:user_id>/',views.quiz_history, name='quiz_history'),
    path('quiz/<int:quiz_id>/review/<int:attempt_id>/',views.review_attempt, name='review_attempt'),
    path('attempt/<int:attempt_id>/review/question/<int:quiz_question_id>/', views.review_response, name='review_response'),

#  Teacher REview
    path('quiz/<int:quiz_id>/teacher/user-attempts/',views.teacher_student_attempt_list,name='teacher_student_attempt_list'),
    path('quiz/response/<int:response_id>/teacher/update-score/',views.update_student_marks,name='update_student_marks'),
    path('quiz/<int:quiz_id>/teacher/user-attempts/search-user/', views.search_quiz_students, name='search_quiz_students'),
    path('quiz-list/<int:course_id>/',views.quiz_list,name='quiz_list'),
    path('quiz-list/<int:course_id>/search-quiz/', views.search_quiz, name='search_quiz'),
]