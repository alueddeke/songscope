#!/usr/bin/env python3
"""
Test script to verify OpenAI API key is working
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
from songscope.ai_feedback_service import FeedbackInterpreter
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_openai_key():
    """Test if OpenAI API key is working"""
    print("🔍 Testing OpenAI API Key...")
    print("=" * 50)
    
    # Check if API key is configured
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        print("❌ ERROR: OpenAI API key not found in settings")
        print("   Make sure OPENAI_API_KEY is set in your environment variables")
        return False
    
    print(f"✅ OpenAI API key found: {api_key[:8]}...{api_key[-4:]}")
    
    # Test the FeedbackInterpreter
    try:
        interpreter = FeedbackInterpreter()
        
        if not interpreter.openai_client:
            print("❌ ERROR: OpenAI client failed to initialize")
            return False
        
        print("✅ OpenAI client initialized successfully")
        
        # Test with a simple feedback message
        test_feedback = "I really like the upbeat tempo and energetic vocals in this song"
        test_track_info = {
            "name": "Test Song",
            "artist": "Test Artist",
            "genre": "Pop"
        }
        
        print(f"\n🧪 Testing with feedback: '{test_feedback}'")
        print("   Track: Test Song by Test Artist (Pop)")
        
        # Make the API call
        result = interpreter.interpret_feedback(test_feedback, test_track_info)
        
        print("✅ OpenAI API call successful!")
        print(f"📊 Interpretation result: {result}")
        
        # Check if the result has expected structure (matching your AI service)
        expected_keys = [
            'tempo_preference', 'mood_preference', 'artist_preference', 
            'genre_preference', 'energy_preference', 'valence_preference',
            'danceability_preference', 'acousticness_preference', 
            'instrumentalness_preference', 'specific_artists', 'specific_genres',
            'time_context', 'activity_context', 'confidence'
        ]
        missing_keys = [key for key in expected_keys if key not in result]
        
        if missing_keys:
            print(f"⚠️  Warning: Missing expected keys in response: {missing_keys}")
        else:
            print("✅ Response structure looks good")
        
        # Check if we got meaningful results
        if result.get('confidence', 0) > 0:
            print("✅ AI interpretation successful with confidence > 0")
        else:
            print("⚠️  Low confidence in AI interpretation")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: OpenAI API test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_openai_call():
    """Test direct OpenAI API call without Django"""
    print("\n🔍 Testing direct OpenAI API call...")
    print("=" * 50)
    
    try:
        from openai import OpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ ERROR: OPENAI_API_KEY environment variable not set")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # Simple test call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'Hello, OpenAI is working!'"}],
            max_tokens=50
        )
        
        content = response.choices[0].message.content
        print(f"✅ Direct API call successful!")
        print(f"🤖 Response: {content}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Direct OpenAI API call failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting OpenAI API Key Test")
    print("=" * 50)
    
    # Test 1: Django integration
    django_test_passed = test_openai_key()
    
    # Test 2: Direct API call
    direct_test_passed = test_direct_openai_call()
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"   Django Integration: {'✅ PASSED' if django_test_passed else '❌ FAILED'}")
    print(f"   Direct API Call: {'✅ PASSED' if direct_test_passed else '❌ FAILED'}")
    
    if django_test_passed and direct_test_passed:
        print("\n🎉 All tests passed! OpenAI API key is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check your OpenAI API key configuration.")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure OPENAI_API_KEY is set in your environment variables")
        print("   2. Verify the API key is valid and has sufficient credits")
        print("   3. Check your internet connection")
        print("   4. Ensure you have the 'openai' package installed: pip install openai")
