import json
import os
from decimal import Decimal
from google import genai
from google.genai import types
from dotenv import load_dotenv
import time
from questions.models import Question
from quizzes.models import Response
import nltk
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from thefuzz import fuzz

try:
    nltk.data.find('punkt')
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

            # stem words
            stemmed_student_words = [self.stemmer.stem(word) for word in student_tokens]

            keyword_found = False

            for kw in sa_obj.required_words:
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

    def grade_with_gemini(self, response, question):
        """
        Grades an open-ended question using Gemini API.
        """
        load_dotenv()
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

        max_mark = question.essayquestionoption.maximum_mark
        question_text = question.question_text
        student_answer = response.answer_given
        expert_answer = question.essayquestionoption.model_answer

        # looks for rubric
        rubric_path = None
        if question.essayquestionoption.marking_rubric and question.essayquestionoption.marking_rubric.name:
            rubric_path = question.essayquestionoption.marking_rubric.path

        prompt = f"""You are an expert professor grading an exam. 
    
        Task: Grade the student's answer against the expert answer and the provided rubric (if provided).
    
        CRITICAL INSTRUCTIONS:
        1. First, write a brief, 2-sentence step-by-step reasoning of what the student got right and wrong based strictly on the rubric.
        2. Then, provide the final grades a number between 0 and {max_mark} inclusive.
        3. Write a brief, 2-sentence constructive feedback of what the student could do to improve their marks for this question.
        4. You MUST return your response as a valid JSON object matching this exact schema:
           {{"reasoning": "your step-by-step logic", "grade": 1, "student_feedback": "your constructive feedback for the student"}}
    
        Question: {question_text}
        Student Answer: {student_answer}
        Expert Answer: {expert_answer}"""

        contents_payload = []
        gemini_file = None

        try:
            if rubric_path and os.path.exists(rubric_path):
                print(f"Uploading rubric to Gemini: {rubric_path}")
                gemini_file = client.files.upload(file=rubric_path)
                contents_payload.append(gemini_file)
            else:
                prompt += "\n\n(No rubric document provided. Use the ExpertAnswer as your strict grading baseline.)"

            contents_payload.append(prompt)

            config = types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )

            models_to_try = ['gemini-3-flash-preview',"gemini-2.5-flash", "gemini-1.5-flash"]
            max_retries = 3
            response_obj = None

            for attempt in range(max_retries):
                try:
                    current_model = models_to_try[0] if attempt == 0 else models_to_try[attempt]

                    print(f"Attempt {attempt + 1}: Sending to {current_model}...")

                    response_obj = client.models.generate_content(
                        model=current_model,
                        contents=contents_payload,
                        config=config
                    )

                    break

                except Exception as e:
                    error_msg = str(e)
                    if "503" in error_msg or "UNAVAILABLE" in error_msg:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            print(f"API Overloaded. Waiting {wait_time} seconds before retry...")
                            time.sleep(wait_time)
                            continue
                    raise e


            raw_response = response_obj.text.strip()

            # Removes any markdown syntax
            if raw_response.startswith('```json'):
                raw_response = raw_response[7:]
            elif raw_response.startswith('```'):
                raw_response = raw_response[3:]
            if raw_response.endswith('```'):
                raw_response = raw_response[:-3]
            raw_response = raw_response.strip()

            json_response = json.loads(raw_response)
            return json_response

        except Exception as e:
            print(f"Gemini API Error: {e}")
            raise e

        finally:
            if gemini_file:
                try:
                    client.files.delete(name=gemini_file.name)
                except Exception as e:
                    print(f"Failed to clean up Gemini file: {e}")