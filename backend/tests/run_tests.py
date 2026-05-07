#!/usr/bin/env python3
"""
Test runner for SongScope backend

Usage:
    python tests/run_tests.py                    # Run all tests
    python tests/run_tests.py unit               # Run only unit tests
    python tests/run_tests.py integration        # Run only integration tests
    python tests/run_tests.py django             # Run Django tests
"""

import sys
import os
import unittest
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

def run_unit_tests():
    """Run unit tests (no external dependencies)"""
    print("🧪 Running Unit Tests")
    print("=" * 50)
    
    # Discover and run unit tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Filter out integration tests
    unit_suite = unittest.TestSuite()
    for test_suite in suite:
        for test_case in test_suite:
            if 'integration' not in str(test_case).lower():
                unit_suite.addTest(test_case)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unit_suite)
    return result.wasSuccessful()

def run_integration_tests():
    """Run integration tests (requires API keys)"""
    print("🔗 Running Integration Tests")
    print("=" * 50)
    
    # Check if we have required environment variables
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set - skipping integration tests")
        return False
    
    # Run integration tests
    from tests.test_openai_integration import run_integration_tests
    return run_integration_tests()

def run_django_tests():
    """Run Django tests"""
    print("🐍 Running Django Tests")
    print("=" * 50)
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        import django
        django.setup()
        
        # Run Django's test command
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'test', 'songscope'])
        return True
    except Exception as e:
        print(f"❌ Django tests failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Running All Tests")
    print("=" * 50)
    
    results = []
    
    # Run unit tests
    results.append(("Unit Tests", run_unit_tests()))
    
    # Run integration tests
    results.append(("Integration Tests", run_integration_tests()))
    
    # Run Django tests
    results.append(("Django Tests", run_django_tests()))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    for test_type, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {test_type}: {status}")
    
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed.")
    
    return all_passed

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == 'unit':
            success = run_unit_tests()
        elif test_type == 'integration':
            success = run_integration_tests()
        elif test_type == 'django':
            success = run_django_tests()
        else:
            print(f"❌ Unknown test type: {test_type}")
            print("Available options: unit, integration, django")
            return False
    else:
        success = run_all_tests()
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
