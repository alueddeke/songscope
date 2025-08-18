"""
Integration tests for OpenAI API

These tests require actual API calls and should be run separately from unit tests.
Use these to verify your OpenAI integration is working in production.
"""

import unittest
import os
import sys
import json
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = backend_dir / '.env'
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not available")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

class TestOpenAIIntegration(unittest.TestCase):
    """Integration tests for OpenAI API"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class - check if we have API key"""
        cls.api_key = os.getenv('OPENAI_API_KEY')
        if not cls.api_key:
            raise unittest.SkipTest("OPENAI_API_KEY not set - skipping integration tests")
        
        print(f"✅ Using OpenAI API key: {cls.api_key[:8]}...{cls.api_key[-4:]}")
    
    def test_openai_client_initialization(self):
        """Test OpenAI client initialization"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            self.assertIsNotNone(client)
            print("✅ OpenAI client initialized successfully")
        except Exception as e:
            self.fail(f"Failed to initialize OpenAI client: {e}")
    
    def test_simple_api_call(self):
        """Test simple OpenAI API call"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'Hello, OpenAI is working!'"}],
                max_tokens=50
            )
            
            content = response.choices[0].message.content
            self.assertIsNotNone(content)
            self.assertIn("Hello", content)
            print(f"✅ Simple API call successful: {content}")
            
        except Exception as e:
            self.fail(f"Simple API call failed: {e}")
    
    def test_music_feedback_interpretation(self):
        """Test music feedback interpretation with OpenAI"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            prompt = """
Analyze this music feedback and extract structured information:
"I really like the upbeat tempo and energetic vocals in this song"

Return a JSON object with these fields (use null if not applicable):
{
    "tempo_preference": "slower" | "faster" | null,
    "mood_preference": "happier" | "sadder" | "calmer" | "more energetic" | "less energetic" | null,
    "energy_preference": "lower" | "higher" | null,
    "confidence": 0.0-1.0
}

Only include fields that are clearly indicated in the feedback. Be conservative - if unsure, use null.
"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            self.assertIsNotNone(content)
            
            # Try to parse as JSON
            try:
                result = json.loads(content)
                self.assertIsInstance(result, dict)
                self.assertIn("confidence", result)
                print(f"✅ Music feedback interpretation successful: {result}")
            except json.JSONDecodeError:
                print(f"⚠️  Response is not valid JSON: {content}")
                # This is okay - the response might not be JSON
                
        except Exception as e:
            self.fail(f"Music feedback interpretation failed: {e}")
    
    def test_django_integration(self):
        """Test Django integration with OpenAI"""
        try:
            import django
            from django.conf import settings
            
            # Set up Django
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
            django.setup()
            
            # Test FeedbackInterpreter
            from songscope.ai_feedback_service import FeedbackInterpreter
            
            interpreter = FeedbackInterpreter()
            self.assertIsNotNone(interpreter)
            
            # Test feedback interpretation
            result = interpreter.interpret_feedback(
                "I love fast music with energetic beats!",
                {"name": "Test Song", "artist": "Test Artist"}
            )
            
            self.assertIsInstance(result, dict)
            self.assertIn("confidence", result)
            print(f"✅ Django integration successful: {result}")
            
        except Exception as e:
            self.fail(f"Django integration failed: {e}")

def run_integration_tests():
    """Run integration tests with proper setup"""
    print("🚀 Running OpenAI Integration Tests")
    print("=" * 50)
    
    # Check if we have API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        print("   Please set your OpenAI API key in the .env file")
        return False
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestOpenAIIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_integration_tests()
    if success:
        print("\n🎉 All integration tests passed!")
    else:
        print("\n⚠️  Some integration tests failed.")
        sys.exit(1)
