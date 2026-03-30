from django.urls import path

from questions import views

urlpatterns = [
    path('create/<int:quiz_id>', views.CreateQuestionView.as_view(), name='create_question'),
    path('create/get-question-partial/',views.get_question_partial,name='get_question_partial'),
    path('create/get-mcq-option/', views.add_mcq_options, name='add_mcq_options'),
]