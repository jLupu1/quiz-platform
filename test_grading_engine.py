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

    # ---------------------------------------------------------
    # 1. SHORT ANSWER LOGIC: EXACT MATCHING & BYPASS
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # 2. SHORT ANSWER LOGIC: KEYWORDS & NLTK
    # ---------------------------------------------------------
    def test_sa_required_words_stemming_and_fuzzy(self):
        """Test NLTK stemming and TheFuzz typo correction."""
        self.mock_sa_obj.use_exact_answer = False
        self.mock_sa_obj.answer_text = "Ignore this"
        self.mock_sa_obj.required_words = ["photosynthesis"]

        # 1. Stem Match ("photosynthetic" shares stem with "photosynthesis")
        self.mock_response.answer_given = "It is photosynthetic."
        # We must mock predict to return 1.0 so it passes the final AI check after keywords
        self.engine.model.predict.return_value = 1.0
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('10.00'))

        # 2. Fuzzy Match Typo ("photosyntesis" missing an 'h')
        self.mock_response.answer_given = "It uses photosyntesis"
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('10.00'))

        # 3. Keyword Missing completely
        self.mock_response.answer_given = "It uses light from the sun."
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('0'))

    # ---------------------------------------------------------
    # 3. SHORT ANSWER LOGIC: AI SIMILARITY SCALING
    # ---------------------------------------------------------
    def test_sa_ai_similarity_scaling(self):
        """Test the partial marks math logic based on Roberta similarity scores."""
        self.mock_sa_obj.use_exact_answer = False
        self.mock_sa_obj.use_case=False
        self.mock_sa_obj.answer_text = "Model text"
        self.mock_response.answer_given = "Student text"

        # 1. Top Boundary (>= 0.65)
        self.engine.model.predict.return_value = 0.80
        print(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa))
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('10.00'))

        # 2. Partial Boundary (e.g., 0.55). Math:
        # zone = 0.19, prog = 0.09, base = 0.473..., final = 0.5 + 0.236 = 0.736 -> * 10 = 7.37
        self.engine.model.predict.return_value = 0.55
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('7.37'))

        # 3. Failing Boundary (< 0.46)
        self.engine.model.predict.return_value = 0.30
        self.assertEqual(self.engine.grade_short_answer(self.mock_response, self.mock_question_sa), Decimal('0'))

    # ---------------------------------------------------------
    # 4. GEMINI API ESSAY LOGIC
    # ---------------------------------------------------------
    @patch('utils.GradingEngine.genai.Client')
    def test_gemini_grading_no_rubric_success(self, MockClient):
        """Test successful Gemini call, stripping markdown syntax."""
        self.mock_response.answer_given = "A good answer."
        self.mock_question.question_text = "Explain X."

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

    @patch('os.path.exists')
    @patch('utils.GradingEngine.genai.Client')
    def test_gemini_grading_with_rubric(self, MockClient, mock_exists):
        """Test Gemini handles rubric file uploading and cleanup properly."""
        mock_exists.return_value = True  # Pretend file exists
        self.mock_essay_obj.marking_rubric = "rubric.pdf"
        self.mock_essay_obj.marking_rubric = "/path/to/rubric.pdf"
        self.mock_response.answer_given = "Answer"

        mock_instance = MockClient.return_value
        mock_file = MagicMock()
        mock_file.name = "gemini_mock_file"
        mock_instance.files.upload.return_value = mock_file

        mock_api_response = MagicMock()
        mock_api_response.text = '{"grade": 20}'
        mock_instance.models.generate_content.return_value = mock_api_response

        result = self.engine.grade_with_gemini(self.mock_response, self.mock_question_essay)

        self.assertEqual(result['grade'], 20)
        # Verify File was Uploaded
        mock_instance.files.upload.assert_called_once_with(file="/path/to/rubric.pdf")
        # Verify finally block cleaned up the file!
        mock_instance.files.delete.assert_called_once_with(name="gemini_mock_file")

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