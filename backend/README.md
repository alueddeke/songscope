# SongScope Backend

A Django-based music recommendation application with AI-powered feedback interpretation and Spotify integration.

## 🏗️ Project Structure

The project follows Django best practices with a clean, modular architecture:

```
backend/
├── config/                          # Django project configuration
│   ├── settings.py                  # Project settings
│   ├── urls.py                      # Main URL routing
│   ├── wsgi.py                      # WSGI application
│   └── asgi.py                      # ASGI application
│
├── apps/                            # Django applications
│   ├── core/                        # Core functionality
│   │   ├── models.py                # Core models (User, Track, etc.)
│   │   ├── views.py                 # API views
│   │   ├── serializers.py           # DRF serializers
│   │   └── migrations/              # Database migrations
│   │
│   ├── ai/                          # AI-powered features
│   │   └── ai_feedback_service.py   # AI feedback interpretation
│   │
│   ├── spotify/                     # Spotify integration
│   │   └── utils.py                 # Spotify API utilities
│   │
│   └── recommendations/             # Recommendation algorithms
│       ├── recommendation_engine.py
│       ├── hybrid_recommendation_engine.py
│       ├── personalization_engine.py
│       ├── track_discovery_engine.py
│       └── feature_extractor.py
│
├── utils/                           # Shared utilities
│   └── logging_config.py            # Logging configuration
│
├── tests/                           # Test suite
│   ├── README.md                    # Test documentation
│   ├── run_tests.py                 # Test runner
│   ├── test_ai_feedback_service.py  # Unit tests
│   └── test_openai_integration.py   # Integration tests
│
├── manage.py                        # Django management script
├── requirements.txt                 # Python dependencies
├── STRUCTURE.md                     # Detailed structure documentation
└── .env                            # Environment variables
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Virtual environment
- Spotify Developer Account
- OpenAI API Key

### Installation

1. **Clone and navigate to backend**
   ```bash
   cd backend
   ```

2. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

## 🧪 Testing

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

## 📱 API Endpoints

### Authentication
- `POST /spotify-login/` - Spotify OAuth login
- `GET /spotify/callback/` - Spotify OAuth callback
- `GET /api/check-auth/` - Check authentication status

### User Management
- `GET /api/user-profile-summary/` - Get user profile
- `PUT /api/update-user-profile/` - Update user profile
- `GET /api/get-user-name/` - Get user name

### Music Data
- `GET /api/user-top-tracks/` - Get user's top tracks
- `GET /api/user-top-artists/` - Get user's top artists
- `GET /api/user-recently-played/` - Get recently played tracks
- `GET /api/artist-details/<id>/` - Get artist details

### Recommendations
- `GET /api/recommendations/` - Get track recommendations
- `GET /api/simple-recommendations/` - Get simple recommendations
- `GET /api/test-spotify-recommendations/` - Test Spotify recommendations

### Feedback
- `POST /api/submit-feedback/` - Submit user feedback
- `POST /api/submit-ai-feedback/` - Submit AI-interpreted feedback
- `GET /api/check-track-feedback/<id>/` - Check track feedback

### Utilities
- `GET /api/csrf-token/` - Get CSRF token
- `POST /api/add-track-to-liked/` - Add track to liked songs

## 🏛️ Architecture

### Apps Overview

#### Core App (`apps/core/`)
- **Purpose**: Foundation functionality
- **Models**: User, Track, UserProfile, UserFeedback, UserPreferences
- **Views**: Authentication, user management, basic CRUD operations

#### AI App (`apps/ai/`)
- **Purpose**: AI-powered features
- **Services**: FeedbackInterpreter for natural language feedback analysis
- **Integration**: OpenAI GPT-4 for intelligent feedback interpretation

#### Spotify App (`apps/spotify/`)
- **Purpose**: Spotify API integration
- **Features**: OAuth authentication, token management, API utilities
- **Utilities**: get_spotipy_client, refresh_spotify_token

#### Recommendations App (`apps/recommendations/`)
- **Purpose**: Music recommendation algorithms
- **Engines**: 
  - HybridRecommendationEngine
  - PersonalizationEngine
  - TrackDiscoveryEngine
  - FeatureExtractor

## 🔧 Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=your_redirect_uri
FRONTEND_URL=your_frontend_url

# Optional
OAUTHLIB_INSECURE_TRANSPORT=False
```

### Django Settings
- **Database**: SQLite (development) / PostgreSQL (production)
- **Authentication**: Session-based with Spotify OAuth
- **CORS**: Configured for frontend integration
- **Logging**: Structured logging with configurable levels

## 🚀 Deployment

### Development
```bash
python manage.py runserver
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

## 📊 Features

### Core Features
- ✅ Spotify OAuth authentication
- ✅ User profile management
- ✅ Track and artist data storage
- ✅ Music recommendation algorithms
- ✅ AI-powered feedback interpretation
- ✅ Comprehensive test suite

### AI Integration
- ✅ Natural language feedback processing
- ✅ OpenAI GPT-4 integration
- ✅ Structured feedback interpretation
- ✅ Confidence scoring
- ✅ Fallback mechanisms

### Recommendation Engine
- ✅ Hybrid recommendation algorithms
- ✅ Personalization based on user preferences
- ✅ Track discovery and exploration
- ✅ Feature extraction and analysis
- ✅ Multi-source recommendation fusion

## 🔍 Monitoring & Logging

### Logging Configuration
- **Level**: Configurable (INFO, DEBUG, WARNING, ERROR)
- **Format**: Structured JSON with timestamps
- **Output**: Console and file logging
- **Categories**: API calls, AI interactions, recommendations

### Rate Limiting
- **Spotify API**: Built-in rate limiting and monitoring
- **OpenAI API**: Cost tracking and usage monitoring
- **User Requests**: Per-user rate limiting

## 🤝 Contributing

### Development Workflow
1. **Create Feature Branch**: `git checkout -b feature/new-feature`
2. **Follow Code Style**: PEP 8, Django conventions
3. **Write Tests**: Unit and integration tests
4. **Update Documentation**: Keep docs current
5. **Submit Pull Request**: With detailed description

### Code Organization
- **Models**: In appropriate app's `models.py`
- **Views**: In appropriate app's `views.py`
- **Utilities**: In `utils/` directory
- **Tests**: In `tests/` directory with clear naming

## 📚 Documentation

- **[STRUCTURE.md](STRUCTURE.md)**: Detailed project structure explanation
- **[tests/README.md](tests/README.md)**: Testing documentation
- **Code Comments**: Comprehensive inline documentation
- **Type Hints**: Full type annotation coverage

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure virtual environment is activated
   - Check import paths match new structure
   - Verify all dependencies are installed

2. **API Key Issues**
   - Verify `.env` file exists and is properly formatted
   - Check API keys are valid and have sufficient credits
   - Ensure environment variables are loaded

3. **Database Issues**
   - Run `python manage.py migrate`
   - Check database file permissions
   - Verify database configuration in settings

4. **Test Failures**
   - Check API keys for integration tests
   - Verify test environment setup
   - Review test logs for specific errors

## 📄 License

This project is part of the SongScope application. See the main project README for licensing information.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the documentation
3. Check existing issues
4. Create a new issue with detailed information

---

**Built with ❤️ using Django, OpenAI, and Spotify APIs**
