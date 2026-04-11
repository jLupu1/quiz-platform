import os
from decimal import Decimal

from questions.models import Question
from quizzes.models import Response

os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

from sentence_transformers import SentenceTransformer, CrossEncoder

print("Booting up AI Grading Engine in memory...")
GLOBAL_MODEL = CrossEncoder('cross-encoder/stsb-roberta-base')

class GradingEngine:
    def __init__(self):
        self.model = GLOBAL_MODEL

    def grade_short_answer(self,response:Response,question:Question):
        sa_obj = question.shortanswerquestionoption


        student_text = response.answer_given.strip()
        model_text = sa_obj.answer_text.strip()

        #exact match
        if sa_obj.use_exact_answer:
            if sa_obj.use_case:
                return sa_obj.maximum_mark if student_text == model_text else Decimal('0.00')
            return sa_obj.maximum_mark if student_text.lower() == model_text.lower() else Decimal('0.00')

        # bypass AI even if selected to mark
        if sa_obj.use_case and student_text == model_text:
            return sa_obj.maximum_mark
        elif sa_obj.use_case and student_text != model_text:
            return Decimal(0)
        elif not sa_obj.use_case and student_text.lower() == model_text.lower():
            return sa_obj.maximum_mark

        # check at least one key word is used
        if sa_obj.required_words:
            keywords = [kw.strip().lower() for kw in sa_obj.required_words]
            student_lower = student_text.lower()

            #if no keywords used then 0 points
            if not any(kw in student_lower for kw in keywords):
                return Decimal(0)

        # use model to get a score
        similarity_score = float(self.model.predict([model_text, student_text]))


        top_boundary = 0.65
        partial_boundary = 0.46

        if similarity_score >= top_boundary:
            return sa_obj.maximum_mark
        elif similarity_score >= partial_boundary:
            # scales partial marks respective to the gap to maximum marks
            zone_size = top_boundary - partial_boundary
            student_progress = similarity_score - partial_boundary

            base_scale = student_progress / zone_size

            final_scale = Decimal(0.5 + (0.5 * base_scale))

            return round(sa_obj.maximum_mark * final_scale, 2)
        else:
            return Decimal(0)