import os
from decimal import Decimal

from dotenv import load_dotenv
from google import genai

from questions.models import Question
from quizzes.models import Response
import nltk
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from thefuzz import fuzz

try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('punkt_tab')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

from sentence_transformers import SentenceTransformer, CrossEncoder

print("Booting up AI Grading Engine in memory...")
GLOBAL_MODEL = CrossEncoder('cross-encoder/stsb-roberta-base')

class GradingEngine:
    def __init__(self):
        self.model = GLOBAL_MODEL
        self.stemmer = PorterStemmer()

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
            # tokenize to separate from punctuation.
            student_tokens = word_tokenize(student_text.lower())
            print(student_tokens)

            # stem words
            stemmed_student_words = [self.stemmer.stem(word) for word in student_tokens]
            print(stemmed_student_words)

            keyword_found = False

            for kw in sa_obj.required_words:
                print(kw)
                kw_lower = kw.strip().lower()
                kw_stem = self.stemmer.stem(kw_lower)

                # check to see if stemmed words appear
                if kw_stem in stemmed_student_words:
                    keyword_found = True
                    break

                # handle typos, check words are close enough
                for token in student_tokens:
                    if fuzz.ratio(kw_lower, token) >= 75:
                        keyword_found = True
                        break

                if keyword_found:
                    break
            if not keyword_found:
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

    def grade_essay(self,response:Response,question:Question):
        essay_obj = question.essayquestionoption
        student_text = response.answer_given.strip()

        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents="Given the question - What is phishing? - What would you grade the answer out of 5 provided by a student - Phishing is a sort of social engineering cyberattack aimed at stealing personal information. "
        )
        print(response.text)