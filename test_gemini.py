import json
import os
from decimal import Decimal

from dotenv import load_dotenv
from google import genai
from google.genai import types

from quizzes.models import QuizQuestion

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def grade_with_gemini(quiz_question : QuizQuestion,response:Response):
    """
    Grades an open-ended question using Gemini API.
    """
    question = quiz_question.question

    max_mark = question.essayquestionoption.maximum_mark
    question_text = question.question_text
    student_answer = response.answer_given
    expert_answer = question.essayquestionoption.model_answer
    rubric_path = question.essayquestionoption.marking_rubric


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

    # 2. Build the contents list
    contents_payload = []
    gemini_file = None

    try:
        # 3. New SDK File Upload Syntax
        if rubric_path and os.path.exists(rubric_path):
            print(f"Uploading rubric to Gemini: {rubric_path}")
            gemini_file = client.files.upload(file=rubric_path)
            contents_payload.append(gemini_file)
        else:
            prompt += "\n\n(No rubric document provided. Use the ExpertAnswer as your strict grading baseline.)"

        contents_payload.append(prompt)
        config = types.GenerateContentConfig(temperature=0.0)

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents_payload,
            config=config
        )
        print(response)
        raw_response = response.text.strip()
        json_response = json.loads(raw_response)


        return json_response

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

    finally:
        if gemini_file:
            try:
                client.files.delete(name=gemini_file.name)
            except Exception as e:
                print(f"Failed to clean up Gemini file: {e}")


if __name__ == "__main__":
    rubric = "1 point for mentioning 'classes', 1 point for mentioning 'objects', 1 point for 'encapsulation'."
    question = "Explain the core concepts of Object-Oriented Programming."
    ex = "OOP relies on classes as blueprints and objects as instances, utilizing encapsulation to hide state."
    std = "It uses classes and objects to build code."

    # Will output something like: "1 1 0"
    grades = grade_with_gemini(question, std, ex)
    print(f"Returned Grades: {grades}")