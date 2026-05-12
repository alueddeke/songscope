#!/usr/bin/env python3
"""
Isolated test script to verify OpenAI API key is working
"""

import os
import sys
from pathlib import Path

def load_env_manually():
    """Load environment variables from .env file manually"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"❌ .env file not found at {env_path}")

def test_openai_isolated():
    """Test OpenAI API in complete isolation"""
    print("🔍 Testing OpenAI API Key in isolation...")
    print("=" * 50)
    
    # Load environment variables manually
    load_env_manually()
    
    # Check environment variable
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        return False
    
    print(f"✅ OpenAI API key found: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        # Import OpenAI in isolation
        from openai import OpenAI
        
        # Create client with minimal configuration
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
        
        # Test token usage
        tokens_used = response.usage.total_tokens
        print(f"📊 Tokens used: {tokens_used}")
        
        return True
        
    except ImportError as e:
        print(f"❌ ERROR: OpenAI package not installed: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: OpenAI API test failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False

def test_environment():
    """Test environment setup"""
    print("🔍 Testing environment...")
    print("=" * 50)
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"Virtual environment: {'✅ Active' if in_venv else '❌ Not active'}")
    
    # Check if openai package is available
    try:
        import openai
        print(f"OpenAI package: ✅ Available (version: {openai.__version__})")
        return True
    except ImportError as e:
        print(f"OpenAI package: ❌ Not available: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Isolated OpenAI API Key Test")
    print("=" * 50)
    
    # Test environment
    env_ok = test_environment()
    
    if env_ok:
        # Test OpenAI API
        api_ok = test_openai_isolated()
        
        print("\n" + "=" * 50)
        print("📋 Test Summary:")
        print(f"   Environment: {'✅ PASSED' if env_ok else '❌ FAILED'}")
        print(f"   OpenAI API: {'✅ PASSED' if api_ok else '❌ FAILED'}")
        
        if api_ok:
            print("\n🎉 OpenAI API key is working correctly!")
        else:
            print("\n⚠️  OpenAI API test failed.")
            print("\n💡 Troubleshooting tips:")
            print("   1. Check if your OpenAI API key is valid")
            print("   2. Verify you have sufficient credits in your OpenAI account")
            print("   3. Check your internet connection")
            print("   4. Try updating the OpenAI package: pip install --upgrade openai")
    else:
        print("\n⚠️  Environment setup failed.")
