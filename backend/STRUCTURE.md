# SongScope Django Project Structure

This document explains the reorganized Django project structure following best practices.

## Overview

The SongScope backend has been reorganized from a confusing nested structure to a clean, modular architecture that follows Django best practices.

## Before vs After

### ❌ Old Structure (Confusing)
```
songscope/
├── backend/                  # Django backend directory
│   ├── backend/             # Django project settings (confusing!)
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── songscope/           # Django app (everything mixed together)
│   │   ├── models.py        # All models
│   │   ├── views.py         # All views
│   │   ├── ai_feedback_service.py
│   │   ├── recommendation_engine.py
│   │   └── ... (many files)
│   └── manage.py
```

### ✅ New Structure (Clean & Organized)
```
songscope/
├── backend/                  # Django backend directory
│   ├── config/              # Django project configuration
│   │   ├── settings.py      # Project settings
│   │   ├── urls.py          # Main URL configuration
│   │   ├── wsgi.py          # WSGI configuration
│   │   └── asgi.py          # ASGI configuration
│   ├── apps/                # Django applications
│   │   ├── core/            # Core functionality
│   │   ├── ai/              # AI-powered features
│   │   ├── spotify/         # Spotify integration
│   │   └── recommendations/ # Recommendation algorithms
│   ├── utils/               # Shared utilities
│   ├── tests/               # Test suite
│   └── manage.py
```

## Detailed Structure

```
backend/
├── config/                          # Django project configuration
│   ├── __init__.py
│   ├── settings.py                  # Project settings
│   ├── urls.py                      # Main URL routing
│   ├── wsgi.py                      # WSGI application
│   └── asgi.py                      # ASGI application
│
├── apps/                            # Django applications
│   ├── core/                        # Core functionality
│   │   ├── __init__.py
│   │   ├── apps.py                  # App configuration
│   │   ├── models.py                # Core models (User, Track, etc.)
│   │   ├── views.py                 # API views
│   │   ├── serializers.py           # DRF serializers
│   │   ├── admin.py                 # Django admin
│   │   └── migrations/              # Database migrations
│   │
│   ├── ai/                          # AI-powered features
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   └── ai_feedback_service.py   # AI feedback interpretation
│   │
│   ├── spotify/                     # Spotify integration
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   └── utils.py                 # Spotify API utilities
│   │
│   └── recommendations/             # Recommendation algorithms
│       ├── __init__.py
│       ├── apps.py
│       ├── recommendation_engine.py
│       ├── hybrid_recommendation_engine.py
│       ├── personalization_engine.py
│       ├── track_discovery_engine.py
│       └── feature_extractor.py
│
├── utils/                           # Shared utilities
│   ├── __init__.py
│   └── logging_config.py            # Logging configuration
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── README.md                    # Test documentation
│   ├── run_tests.py                 # Test runner
│   ├── test_ai_feedback_service.py  # Unit tests
│   ├── test_openai_integration.py   # Integration tests
│   └── backup/                      # Old test files
│
├── manage.py                        # Django management script
├── requirements.txt                 # Python dependencies
└── .env                            # Environment variables
```

## Django Best Practices Explained

### 1. **Separation of Concerns**
Each app has a specific responsibility:
- **Core**: User management, basic models, API endpoints
- **AI**: AI-powered features and services
- **Spotify**: Spotify API integration
- **Recommendations**: Music recommendation algorithms

### 2. **App Organization**
```
apps/
├── core/           # Core functionality (users, tracks, etc.)
├── ai/             # AI features
├── spotify/        # External API integration
└── recommendations/ # Business logic
```

### 3. **Configuration Management**
```
config/
├── settings.py     # All project settings
├── urls.py         # Main URL routing
├── wsgi.py         # Production deployment
└── asgi.py         # Async support
```

### 4. **Utility Organization**
```
utils/
├── logging_config.py    # Shared logging
└── ...                 # Other shared utilities
```

## When to Create New Folders/Apps

### Create a New Django App When:
1. **New Feature Domain**: Different business logic (e.g., `analytics`, `notifications`)
2. **External Integration**: New third-party service (e.g., `apple_music`, `youtube`)
3. **Separate Functionality**: Distinct feature set (e.g., `playlists`, `social`)

### Create a New Folder When:
1. **Shared Utilities**: Common functions used across apps (`utils/`)
2. **Configuration**: Project-level settings (`config/`)
3. **Tests**: Organized test structure (`tests/`)
4. **Documentation**: Project docs (`docs/`)

## App Responsibilities

### Core App (`apps/core/`)
- **Purpose**: Foundation functionality
- **Contains**: User models, basic API endpoints, authentication
- **Models**: `User`, `Track`, `UserProfile`, `UserFeedback`
- **Views**: Authentication, user management, basic CRUD

### AI App (`apps/ai/`)
- **Purpose**: AI-powered features
- **Contains**: OpenAI integration, feedback interpretation
- **Services**: `FeedbackInterpreter`, AI analysis

### Spotify App (`apps/spotify/`)
- **Purpose**: Spotify API integration
- **Contains**: OAuth, API utilities, token management
- **Utilities**: `get_spotipy_client`, `refresh_spotify_token`

### Recommendations App (`apps/recommendations/`)
- **Purpose**: Music recommendation algorithms
- **Contains**: Recommendation engines, personalization
- **Engines**: `HybridRecommendationEngine`, `PersonalizationEngine`

## Import Patterns

### Within Apps
```python
# Good - relative imports within same app
from .models import User
from .serializers import UserSerializer
```

### Between Apps
```python
# Good - absolute imports between apps
from apps.core.models import User
from apps.spotify.utils import get_spotipy_client
```

### External Libraries
```python
# Good - standard library and third-party imports
import os
import logging
from django.conf import settings
from rest_framework import serializers
```

## URL Organization

### Main URLs (`config/urls.py`)
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.core.urls')),
    path('spotify/', include('apps.spotify.urls')),
]
```

### App URLs (Future)
```python
# apps/core/urls.py
urlpatterns = [
    path('users/', views.UserViewSet.as_view()),
    path('tracks/', views.TrackViewSet.as_view()),
]

# apps/spotify/urls.py
urlpatterns = [
    path('login/', views.spotify_login),
    path('callback/', views.spotify_callback),
]
```

## Testing Structure

```
tests/
├── test_ai_feedback_service.py    # Unit tests (mocked)
├── test_openai_integration.py     # Integration tests (real API)
└── run_tests.py                   # Test runner
```

### Test Types
- **Unit Tests**: Test individual components (mocked dependencies)
- **Integration Tests**: Test real API interactions
- **Django Tests**: Test Django-specific functionality

## Environment Management

### Environment Variables
```bash
# .env file
OPENAI_API_KEY=your_key_here
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

### Settings Configuration
```python
# config/settings.py
from decouple import config

OPENAI_API_KEY = config('OPENAI_API_KEY', default=None)
SPOTIFY_CLIENT_ID = config('SPOTIFY_CLIENT_ID')
```

## Running the Project

### Development
```bash
# Activate virtual environment
source venv/bin/activate

# Run Django server
python manage.py runserver

# Run tests
python tests/run_tests.py
```

### Production
```bash
# Collect static files
python manage.py collectstatic

# Run migrations
python manage.py migrate

# Start with gunicorn
gunicorn config.wsgi:application
```

## Benefits of This Structure

1. **Clarity**: Clear separation of concerns
2. **Maintainability**: Easy to find and modify code
3. **Scalability**: Easy to add new features
4. **Testing**: Organized test structure
5. **Deployment**: Clear configuration management
6. **Team Collaboration**: Multiple developers can work on different apps

## Migration Guide

### For Developers
1. **Update Imports**: Change from `songscope.models` to `apps.core.models`
2. **Test Thoroughly**: Run all tests after restructuring
3. **Update Documentation**: Keep this structure guide updated

### For New Features
1. **Choose App**: Determine which app the feature belongs to
2. **Create Models**: Add models to appropriate app
3. **Add Views**: Create views in the app
4. **Update URLs**: Add URL patterns
5. **Write Tests**: Add tests to test suite

This structure follows Django best practices and makes the codebase much more maintainable and scalable!
