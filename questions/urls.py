from django.urls import path

from questions import views
from quizzes.models import QuizQuestion

urlpatterns = [
    path('create/<int:quiz_id>', views.CreateQuestionView.as_view(), name='create_question'),
    path('create/get-question-partial/',views.get_question_partial,name='get_question_partial'),
    path('create/get-mcq-option/', views.add_mcq_options, name='add_mcq_options'),
    path('view/<int:quiz_id>/',views.ViewQuestions.as_view(), name='view_questions'),
    # QuizQuestion Id
    path('edit/<int:pk>/',views.EditQuestion.as_view(), name='edit_question'),
    path('delete/<int:pk>/',views.delete_question, name='delete_question'),
    path('course/<int:course_id>/question-bank',views.question_bank,name='question_bank'),
    path('course/<int:course_id>/question-bank/search-question',views.search_questions,name='search_questions'),
]