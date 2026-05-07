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
