from questions.models import QuestionType
from quizzes.models import Attempt
from utils.GradingEngine import GradingEngine


def process_quiz_submission(attempt:Attempt):
    ai_engine = GradingEngine()

    for response in attempt.responses.all():
        question = response.quiz_question.question

        if question.question_type in [QuestionType.MCQ, QuestionType.EITHER_OR]:
            response.auto_grade()


        elif question.question_type == QuestionType.SHORT_ANSWER:
            short_answer_obj = question.shortanswerquestionoption
            if short_answer_obj.is_auto_mark:
                try:
                    marks = ai_engine.grade_short_answer(response,question)

                    response.marks_given = marks
                    response.save()
                except Exception as e:
                    response.marks_given = None
                    response.save()

    attempt.calculate_total_score()