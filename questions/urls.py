from django.urls import path

from questions.views import CreateQuestionView

urlpatterns = [
    path('create/<int:quiz_id>', CreateQuestionView.as_view(), name='create_question'),
]