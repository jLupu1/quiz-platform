import json
from decimal import Decimal
from unittest.mock import MagicMock, patch, call
from django.test import TestCase

# We patch the heavy ML model at the import level so it doesn't download during testing
with patch('sentence_transformers.CrossEncoder'):
    from utils.GradingEngine import GradingEngine


class GradingEngineTests(TestCase):
    def setUp(self):
        self.engine = GradingEngine()
        # Mock the internal model to intercept prediction scores
        self.engine.model = MagicMock()

        # 1. Mock Django Models for Short Answer
        self.mock_response = MagicMock()
        self.mock_question_sa = MagicMock()
        self.mock_question_essay = MagicMock()

        self.mock_sa_obj = MagicMock()

        # Default SA Setup
        self.mock_sa_obj.maximum_mark = Decimal('10.00')
        self.mock_question_sa.shortanswerquestionoption = self.mock_sa_obj

        # 2. Mock Django Models for Essay / Gemini
        self.mock_essay_obj = MagicMock()
        self.mock_essay_obj.maximum_mark = Decimal('20.00')
        self.mock_essay_obj.model_answer = "The expert answer."
        self.mock_essay_obj.marking_rubric = None
        self.mock_question_essay.essayquestionoption = self.mock_essay_obj


    def test_sa_exact_match_case_sensitive(self):
        """Test exact match with strict casing."""
        self.mock_sa_obj.use_exact_answer = True
        self.mock_sa_obj.use_case = True
        self.mock_sa_obj.answer_text = "Python"

        # Success
        self.mock_response.answer_given = "Python"
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('10.00'))

        # Failure (Wrong Case)
        self.mock_response.answer_given = "python"
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('0.00'))

    def test_sa_exact_match_case_insensitive(self):
        """Test exact match ignoring casing."""
        self.mock_sa_obj.use_exact_answer = True
        self.mock_sa_obj.use_case = False
        self.mock_sa_obj.answer_text = "Python"

        self.mock_response.answer_given = "PYTHON"
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('10.00'))

    def test_sa_bypass_ai_matching(self):
        """Test exact matching fallback when AI is enabled but exact match hits first."""
        self.mock_sa_obj.use_exact_answer = False
        self.mock_sa_obj.answer_text = "Django"

        # Case sensitive success
        self.mock_sa_obj.use_case = True
        self.mock_response.answer_given = "Django"
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('10.00'))

        # Case sensitive failure -> should return 0
        self.mock_response.answer_given = "django"
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('0'))

        # Case insensitive success
        self.mock_sa_obj.use_case = False
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('10.00'))


    @patch('utils.GradingEngine.genai.Client')
    def test_gemini_grading_no_rubric_success(self, MockClient):
        """Test successful Gemini call, stripping markdown syntax."""
        self.mock_response.answer_given = "A good answer."
        self.mock_question_sa.question_text = "Explain X."

        # Setup Mock API Response
        mock_instance = MockClient.return_value
        mock_api_response = MagicMock()
        # Test markdown stripping by wrapping JSON
        mock_api_response.text = '```json\n{"reasoning": "Good", "grade": 15, "student_feedback": "Keep it up"}\n```'
        mock_instance.models.generate_content.return_value = mock_api_response

        result = self.engine.grade_with_gemini(self.mock_response, self.mock_question_essay)

        self.assertEqual(result['grade'], 15)
        self.assertEqual(result['reasoning'], "Good")
        # Ensure it didn't try to upload a rubric file
        mock_instance.files.upload.assert_not_called()

    @patch('time.sleep')  # Don't actually sleep during tests
    @patch('utils.GradingEngine.genai.Client')
    def test_gemini_api_overload_retry_logic(self, MockClient, mock_sleep):
        """Test the 503 UNAVAILABLE exponential backoff retry loop."""
        mock_instance = MockClient.return_value

        mock_api_response = MagicMock()
        mock_api_response.text = '{"grade": 10}'

        # Side effect: First call raises 503, Second call succeeds
        mock_instance.models.generate_content.side_effect = [
            Exception("503 Server Error: UNAVAILABLE"),
            mock_api_response
        ]

        result = self.engine.grade_with_gemini(self.mock_response, self.mock_question_essay)

        self.assertEqual(result['grade'], 10)
        # Verify it retried exactly twice
        self.assertEqual(mock_instance.models.generate_content.call_count, 2)
        # Verify exponential backoff sleep was called
        mock_sleep.assert_called_once_with(1)  # wait_time = 2**0 = 1

    @patch('utils.GradingEngine.genai.Client')
    def test_gemini_unrecoverable_error(self, MockClient):
        """Test that non-503 errors raise immediately."""
        mock_instance = MockClient.return_value
        mock_instance.models.generate_content.side_effect = Exception("Auth Error")

        with self.assertRaises(Exception) as context:
            self.engine.grade_with_gemini(self.mock_response, self.mock_question_essay)

        self.assertTrue("Auth Error" in str(context.exception))