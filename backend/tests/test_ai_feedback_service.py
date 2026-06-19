"""
Unit tests for AI Feedback Service

This module tests the FeedbackInterpreter class and its methods.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = backend_dir / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

class TestFeedbackInterpreter(unittest.TestCase):
    """Test cases for FeedbackInterpreter class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the OpenAI import
        self.mock_openai_patcher = patch('openai.OpenAI')
        self.mock_openai = self.mock_openai_patcher.start()
        
        # Import after mocking
        from apps.ai.ai_feedback_service import FeedbackInterpreter
        self.FeedbackInterpreter = FeedbackInterpreter
    
    def tearDown(self):
        """Clean up after tests"""
        self.mock_openai_patcher.stop()
    
    def test_initialization_with_api_key(self):
        """Test FeedbackInterpreter initialization with valid API key"""
        # Mock settings
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = 'test-api-key'
            
            interpreter = self.FeedbackInterpreter()
            
            # Check that OpenAI client was created
            self.mock_openai.assert_called_once_with(api_key='test-api-key')
            self.assertIsNotNone(interpreter.openai_client)
    
    def test_initialization_without_api_key(self):
        """Test FeedbackInterpreter initialization without API key"""
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            
            interpreter = self.FeedbackInterpreter()
            
            # Check that OpenAI client was not created
            self.assertIsNone(interpreter.openai_client)
    
    def test_interpret_feedback_success(self):
        """Test successful feedback interpretation"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "tempo_preference": "faster",
            "mood_preference": "happier",
            "energy_preference": "higher",
            "confidence": 0.8
        })
        mock_response.usage.total_tokens = 100
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        self.mock_openai.return_value = mock_client
        
        # Mock settings
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = 'test-api-key'
            
            interpreter = self.FeedbackInterpreter()
            result = interpreter.interpret_feedback("I love fast music!")
            
            # Verify the result
            self.assertEqual(result["tempo_preference"], "faster")
            self.assertEqual(result["mood_preference"], "happier")
            self.assertEqual(result["confidence"], 0.8)
    
    def test_interpret_feedback_fallback(self):
        """Test fallback interpretation when OpenAI fails"""
        # Mock OpenAI to raise an exception
        self.mock_openai.side_effect = Exception("API Error")
        
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = 'test-api-key'
            
            interpreter = self.FeedbackInterpreter()
            result = interpreter.interpret_feedback("I love fast music!")
            
            # Should use fallback interpretation
            self.assertIn("tempo_preference", result)
            self.assertIn("confidence", result)
            self.assertEqual(result["confidence"], 0.3)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = 'test-api-key'

            interpreter = self.FeedbackInterpreter()

            # Mock rate limiter to return False (limit exceeded)
            interpreter.rate_limiter.check_openai_limit = Mock(return_value=False)

            # Should raise RateLimitExceeded
            with self.assertRaises(Exception):  # RateLimitExceeded
                interpreter.interpret_feedback("test feedback")

    def test_build_prompt_contains_overall_sentiment(self):
        """System prompt schema includes overall_sentiment field"""
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            interpreter = self.FeedbackInterpreter()
            system_prompt = interpreter._build_system_prompt()
            self.assertIn("overall_sentiment", system_prompt)

    def test_system_prompt_has_vocabulary_mapping(self):
        """System prompt vocabulary table covers vocals, energetic, genre avoidance"""
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            interpreter = self.FeedbackInterpreter()
            sp = interpreter._build_system_prompt()
            self.assertIn("less_instrumental", sp)
            self.assertIn("more_instrumental", sp)
            self.assertIn("energy_preference", sp)
            self.assertIn("avoid_genre", sp)

    def test_system_prompt_has_negation_rule(self):
        """System prompt explicitly handles 'no X' / 'without X' negation"""
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            interpreter = self.FeedbackInterpreter()
            sp = interpreter._build_system_prompt()
            self.assertIn("NEGATION", sp)

    def test_few_shot_messages_structure(self):
        """Few-shot messages are valid user/assistant pairs with JSON assistant turns"""
        import json as _json
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            interpreter = self.FeedbackInterpreter()
            msgs = interpreter._get_few_shot_messages()
            roles = [m["role"] for m in msgs]
            self.assertEqual(roles, ["user", "assistant", "user", "assistant", "user", "assistant", "user", "assistant"])
            for m in msgs:
                if m["role"] == "assistant":
                    parsed = _json.loads(m["content"])
                    self.assertIn("instrumentalness_preference", parsed)
                    self.assertIn("overall_sentiment", parsed)

    def test_fallback_interprets_vocals(self):
        """Fallback correctly maps 'with vocals' to less_instrumental"""
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            interpreter = self.FeedbackInterpreter()
            result = interpreter._fallback_interpretation("something with vocals please")
            self.assertEqual(result["instrumentalness_preference"], "less_instrumental")

    def test_fallback_interprets_no_vocals(self):
        """Fallback correctly maps 'no vocals' to more_instrumental"""
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            interpreter = self.FeedbackInterpreter()
            result = interpreter._fallback_interpretation("no vocals, purely instrumental")
            self.assertEqual(result["instrumentalness_preference"], "more_instrumental")

    def test_fallback_interprets_energetic(self):
        """Fallback correctly maps 'more energetic' to energy_preference higher"""
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            interpreter = self.FeedbackInterpreter()
            result = interpreter._fallback_interpretation("something more energetic please")
            self.assertEqual(result["energy_preference"], "higher")

    def test_fallback_interprets_genre_avoidance(self):
        """Fallback extracts 'no ambient' as genre avoidance"""
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            interpreter = self.FeedbackInterpreter()
            result = interpreter._fallback_interpretation("no ambient music please")
            self.assertEqual(result["genre_preference"], "avoid_genre")
            self.assertIn("ambient", result["specific_genres"])

    def test_fallback_interpretation_contains_overall_sentiment_key(self):
        """Test that fallback interpretation always includes overall_sentiment key"""
        self.mock_openai.side_effect = Exception("API Error")
        with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = 'test-api-key'
            interpreter = self.FeedbackInterpreter()
            result = interpreter.interpret_feedback("I love fast music!")
            self.assertIn("overall_sentiment", result)

class TestRateLimitMonitor(unittest.TestCase):
    """Test cases for RateLimitMonitor class"""
    
    def setUp(self):
        from apps.ai.ai_feedback_service import RateLimitMonitor
        self.RateLimitMonitor = RateLimitMonitor
    
    def test_rate_limit_check(self):
        """Test rate limit checking"""
        monitor = self.RateLimitMonitor()
        
        # Should allow first request
        self.assertTrue(monitor.check_openai_limit())
        
        # Should allow multiple requests within limit
        for _ in range(10):
            self.assertTrue(monitor.check_openai_limit())
    
    def test_cost_logging(self):
        """Test cost logging functionality"""
        monitor = self.RateLimitMonitor()
        
        # Log some costs
        monitor.log_cost(1000)  # 1000 tokens
        monitor.log_cost(2000)  # 2000 tokens
        
        # Should not exceed daily limit
        self.assertLess(monitor.daily_cost, monitor.max_daily_cost)

if __name__ == '__main__':
    unittest.main()
