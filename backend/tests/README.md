# SongScope Backend Tests

This directory contains comprehensive tests for the SongScope backend application.

## Test Structure

```
tests/
├── __init__.py                    # Makes tests a Python package
├── README.md                      # This file
├── run_tests.py                   # Main test runner
├── test_ai_feedback_service.py    # Unit tests for AI feedback service
├── test_openai_integration.py     # Integration tests for OpenAI API
└── backup/                        # Old test files (for reference)
    ├── simple_openai_test.py
    ├── isolated_openai_test.py
    └── test_openai.py
```

## Test Types

### 1. Unit Tests (`test_ai_feedback_service.py`)
- **Purpose**: Test individual components in isolation
- **Dependencies**: Mocked external services (no API calls)
- **Speed**: Fast execution
- **Use Case**: Development, CI/CD

### 2. Integration Tests (`test_openai_integration.py`)
- **Purpose**: Test integration with external services
- **Dependencies**: Real API calls to OpenAI
- **Speed**: Slower (network calls)
- **Use Case**: Production verification, end-to-end testing

### 3. Django Tests
- **Purpose**: Test Django-specific functionality
- **Dependencies**: Django ORM, database
- **Speed**: Medium
- **Use Case**: Model validation, view testing

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Test Types
```bash
# Unit tests only (fast, no API calls)
python tests/run_tests.py unit

# Integration tests only (requires API keys)
python tests/run_tests.py integration

# Django tests only
python tests/run_tests.py django
```

### Run Individual Test Files
```bash
# Run specific test file
python -m unittest tests.test_ai_feedback_service
python -m unittest tests.test_openai_integration
```

## Environment Setup

### Required Environment Variables
```bash
# .env file should contain:
OPENAI_API_KEY=your_openai_api_key_here
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
# ... other variables
```

### Virtual Environment
```bash
# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install -r requirements.txt
```

## Test Best Practices

### 1. Unit Tests
- Mock external dependencies
- Test edge cases and error conditions
- Keep tests fast and isolated
- Use descriptive test names

### 2. Integration Tests
- Test real API interactions
- Handle rate limits gracefully
- Skip tests if API keys are missing
- Log API costs for monitoring

### 3. Test Organization
- Group related tests in classes
- Use setUp() and tearDown() for fixtures
- Follow AAA pattern (Arrange, Act, Assert)
- Add docstrings to test methods

## Example Test Output

### Successful Unit Tests
```
🧪 Running Unit Tests
==================================================
test_initialization_with_api_key ... ok
test_interpret_feedback_success ... ok
test_rate_limiting ... ok
----------------------------------------------------------------------
Ran 7 tests in 0.176s
OK
```

### Successful Integration Tests
```
🔗 Running Integration Tests
==================================================
test_openai_client_initialization ... ✅ OpenAI client initialized successfully
test_simple_api_call ... ✅ Simple API call successful: Hello, OpenAI is working!
test_music_feedback_interpretation ... ✅ Music feedback interpretation successful
----------------------------------------------------------------------
Ran 4 tests in 6.643s
OK
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Ensure `.env` file exists in backend directory
   - Check that `OPENAI_API_KEY` is set correctly

2. **Django Settings Not Configured**
   - Make sure `DJANGO_SETTINGS_MODULE` is set
   - Run tests from the backend directory

3. **Import Errors**
   - Ensure virtual environment is activated
   - Check that all dependencies are installed

4. **Rate Limiting**
   - Integration tests may fail if API rate limits are exceeded
   - Check your OpenAI account usage

### Debug Mode
```bash
# Run with verbose output
python -m unittest -v tests.test_ai_feedback_service

# Run specific test method
python -m unittest tests.test_ai_feedback_service.TestFeedbackInterpreter.test_initialization_with_api_key
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py` for test files
2. **Add docstrings**: Describe what each test does
3. **Mock external dependencies**: In unit tests
4. **Handle errors gracefully**: In integration tests
5. **Update this README**: Document new test types or patterns

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Unit Tests
  run: python tests/run_tests.py unit

- name: Run Integration Tests
  run: python tests/run_tests.py integration
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```
