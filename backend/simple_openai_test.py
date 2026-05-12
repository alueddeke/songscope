#!/usr/bin/env python3
"""
Simple test script to verify OpenAI API key is working
"""

import os
import sys
from pathlib import Path

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

def test_openai_direct():
    """Test OpenAI API directly"""
    print("🔍 Testing OpenAI API Key directly...")
    print("=" * 50)
    
    # Check environment variable
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("   Please set it with: export OPENAI_API_KEY='your-key-here'")
        print("   Or add it to your .env file")
        return False
    
    print(f"✅ OpenAI API key found: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        from openai import OpenAI
        
        # Create client
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client created successfully")
        
        # Test simple API call
        print("\n🧪 Making test API call...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'Hello, OpenAI is working!'"}],
            max_tokens=50
        )
        
        content = response.choices[0].message.content
        print(f"✅ API call successful!")
        print(f"🤖 Response: {content}")
        
        # Test with a more complex prompt
        print("\n🧪 Testing with music feedback interpretation...")
        feedback_prompt = """
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
        
        response2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": feedback_prompt}],
            max_tokens=200,
            temperature=0.1
        )
        
        content2 = response2.choices[0].message.content
        print(f"✅ Music feedback interpretation successful!")
        print(f"📊 Response: {content2}")
        
        return True
        
    except ImportError:
        print("❌ ERROR: OpenAI package not installed")
        print("   Install with: pip install openai")
        return False
    except Exception as e:
        print(f"❌ ERROR: OpenAI API test failed: {str(e)}")
        return False

def test_environment_setup():
    """Test environment setup"""
    print("🔍 Testing environment setup...")
    print("=" * 50)
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"Virtual environment: {'✅ Active' if in_venv else '❌ Not active'}")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check if openai package is available
    try:
        import openai
        print(f"OpenAI package: ✅ Available (version: {openai.__version__})")
    except ImportError:
        print("OpenAI package: ❌ Not available")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Simple OpenAI API Key Test")
    print("=" * 50)
    
    # Test environment
    env_ok = test_environment_setup()
    
    if env_ok:
        # Test OpenAI API
        api_ok = test_openai_direct()
        
        print("\n" + "=" * 50)
        print("📋 Test Summary:")
        print(f"   Environment: {'✅ PASSED' if env_ok else '❌ FAILED'}")
        print(f"   OpenAI API: {'✅ PASSED' if api_ok else '❌ FAILED'}")
        
        if api_ok:
            print("\n🎉 OpenAI API key is working correctly!")
        else:
            print("\n⚠️  OpenAI API test failed. Please check your configuration.")
    else:
        print("\n⚠️  Environment setup failed. Please check your virtual environment and packages.")
