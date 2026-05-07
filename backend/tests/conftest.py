"""
Shared pytest fixtures and Django setup for backend tests.
Per Phase 1 RESEARCH: DJANGO_SETTINGS_MODULE must be 'config.settings' (NOT 'backend.settings').
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path so `apps.*` and `config.*` imports resolve.
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load .env if present (matches the pattern in test_ai_feedback_service.py).
try:
    from dotenv import load_dotenv
    env_path = backend_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Django settings module path is 'config.settings' — confirmed in backend/manage.py.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()
