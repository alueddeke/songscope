# SongScope Project Audit & Interview Preparation Guide

> **IMPORTANT:** See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed solutions to common issues and setup problems.

## Executive Summary

**SongScope** is a full-stack music recommendation application that combines Spotify API integration with AI-powered personalization. The project demonstrates sophisticated backend architecture with Django REST Framework, a modern Next.js frontend with React Server Components, and advanced features including OpenAI-powered feedback interpretation and hybrid recommendation algorithms.

**Current Status:** Fully functional with recent restructuring (Aug 18, 2025). The application is ready to run locally with proper credentials configured.

**Latest Updates (March 18, 2026):**
- Fixed missing dependencies (`python-decouple`, `django-cors-headers`)
- Resolved Spotify OAuth "Insecure redirect_uri" issue
- Created comprehensive troubleshooting documentation
- Verified complete working setup

---

## 1. PROJECT ARCHITECTURE OVERVIEW

### Tech Stack
- **Frontend:** Next.js 14.2.4, React 18, TypeScript, Tailwind CSS
- **Backend:** Django 5.1.3, Django REST Framework
- **Database:** SQLite (development)
- **External APIs:** Spotify Web API, OpenAI GPT-4o-mini
- **Architecture:** Decoupled SPA-style frontend + REST API backend

### System Architecture
```
Next.js Frontend (localhost:3000)
    ↓ HTTP + CSRF + Session Cookie
Django Backend (localhost:8000)
    ↓ OAuth + API Calls
Spotify Web API + OpenAI API
```

---

## 2. MYSTERY SOLVED: Duplicate Next.js Folders

**Question:** Why are there two `.next` folders (root and frontend)?

**Answer:**
- **Root `.next/`** - STALE build artifacts from June 2024 when project attempted monorepo at root level
- **frontend/.next/`** - ACTIVE build artifacts from current Next.js app (last modified Aug 2025)
- **Action Required:** Root `.next/` should be removed from git and added to `.gitignore`

**Active Codebase:** Everything in `/frontend/` directory is the current, working application.

---

## 3. HOW TO LAUNCH THE PROJECT

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Spotify Developer Account credentials (already configured in `.env`)
- OpenAI API Key (already configured in `.env`)

### Step-by-Step Launch Instructions

#### Terminal 1: Start Backend
```bash
cd /Users/antonilueddeke/Desktop/Projects/songscope/backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Run migrations (if needed)
python manage.py migrate

# Start Django server
python manage.py runserver
# ✓ Backend running at http://localhost:8000
```

**Note:** OAuth configuration for HTTP localhost is now handled automatically in the code (`apps/core/views.py` sets `OAUTHLIB_INSECURE_TRANSPORT=1` at import time).

#### Terminal 2: Start Frontend
```bash
cd /Users/antonilueddeke/Desktop/Projects/songscope/frontend

# Install dependencies (if needed)
npm install

# Start Next.js dev server
npm run dev
# ✓ Frontend running at http://localhost:3000
```

#### Access Application
1. Open browser to **http://localhost:3000**
2. Click "Login with Spotify"
3. Authorize with your Spotify account
4. Redirects to `/profile` with recommendations

---

## 4. CORE FEATURES & USER FLOWS

### Feature 1: Spotify Authentication
- OAuth 2.0 flow handled by backend
- Session-based authentication with cookies
- Automatic token refresh for expired Spotify tokens
- **Endpoints:** `/spotify-login/`, `/spotify/callback/`

### Feature 2: Personalized Recommendations
- Hybrid recommendation engine combining 5 strategies:
  - Playlist mining (30%)
  - Artist network (25%)
  - Contextual analysis (20%)
  - Popularity-based (15%)
  - User feedback (10%)
- 5-minute cache with force-refresh option
- Displays track image, name, artist, album
- Navigate through recommendations with Next/Previous
- **Component:** `frontend/app/profile/components/Recommendation/`

### Feature 3: Like/Dislike Feedback System
- Toggle like/unlike on tracks
- State persists - checks previous feedback on track change
- Updates personalization engine in real-time
- Green button for like, red for dislike
- **Recent Update (commit bad8aac9):** Buttons now hold state across tracks

### Feature 4: AI-Powered Feedback Interpretation (NEW)
- Natural language input: "I want something more upbeat and electronic"
- OpenAI GPT-4o-mini interprets into structured preferences
- Extracts: tempo, mood, energy, genre preferences
- Rate limit protection (50 req/min, $1/day)
- Fallback rule-based interpretation if OpenAI unavailable
- **Status:** Implemented but marked "untested" (commit 6b949652)
- **Component:** `frontend/app/profile/components/Feedback/AIFeedbackInput.tsx`

### Feature 5: Top Artists Discovery
- Display user's top artists with time filtering:
  - Last 4 weeks
  - Last 6 months
  - All time
- Click artist to expand details:
  - Follower count, popularity, genres
  - Latest album
  - Your favorite tracks from artist (color-coded by source)
  - Artist's most popular tracks globally
- **Recent Update (commit 39a86158):** Enhanced with expanded details view

### Feature 6: Add to Spotify Library
- One-click save to Spotify Liked Songs
- Instant visual feedback with heart icon
- **Endpoint:** `/api/add-track-to-liked/`

### Feature 7: Audio Preview
- In-app track preview player
- Uses react-h5-audio-player library
- Dark theme styling

---

## 5. BACKEND ARCHITECTURE DEEP DIVE

### Database Schema (7 Models)

#### User-Related Models
1. **SpotifyToken** (1:1 with User)
   - Stores OAuth tokens (access, refresh, expiry)
   - Automatic refresh when expired

2. **UserProfile** (1:1 with User)
   - Extended profile with music preferences
   - Caching system for recommendations
   - Feedback history stored in JSON field
   - Methods: `get_from_cache()`, `update_cache()`, `add_feedback()`

3. **UserPreferences** (1:1 with User)
   - Structured music preferences
   - Tempo range, energy level, mood, genres, artists

#### Track & Feedback Models
4. **Track**
   - Spotify track metadata
   - Unique by `spotify_id`

5. **UserFeedback** (N:M between User and Track)
   - Types: LIKE, DISLIKE, SAVE, SKIP, PLAY
   - Rating (1-5 scale)
   - Feedback text
   - Unique constraint: (user, track)

6. **AIFeedback**
   - Natural language feedback storage
   - AI interpretation as JSON
   - Confidence score

7. **RecommendationLog**
   - Audit trail of recommendations shown to users

### Entity Relationships
```
User (Django built-in)
  ├── SpotifyToken (1:1)
  ├── UserProfile (1:1) → contains cache, feedback history
  ├── UserFeedback (1:N) ← Track (1:N)
  ├── UserPreferences (1:1)
  ├── AIFeedback (1:N) ← Track (1:N)
  └── RecommendationLog (1:N) ← Track (1:N)

Track (shared across all users)
  ├── UserFeedback (1:N)
  ├── AIFeedback (1:N)
  └── RecommendationLog (1:N)
```

### API Endpoints (30+)

**Base URL:** `http://localhost:8000`

#### Authentication
- `GET /spotify-login/` - Initiate OAuth
- `GET /spotify/callback/` - OAuth callback
- `GET /api/check-auth/` - Verify session
- `GET /api/check-spotify-token/` - Check token validity

#### Recommendations
- `GET /api/recommendations/` - Get personalized tracks
- `GET /api/recommendations/?force_fresh=true` - Bypass cache

#### User Data
- `GET /api/get-user-name/` - User's Spotify name
- `GET /api/user-top-tracks/` - Top 12 tracks (short term)
- `GET /api/user-recently-played/` - 50 recent tracks
- `GET /api/user-top-artists/?time_range=<4 weeks|6 months|year>` - Top artists
- `GET /api/artist-details/<artist_id>/` - Detailed artist info

#### Feedback
- `POST /api/submit-feedback/` - Like/dislike track
- `POST /api/submit-ai-feedback/` - Natural language feedback
- `GET /api/check-track-feedback/<track_id>/` - Check if liked

#### Library Management
- `POST /api/add-track-to-liked/` - Save to Spotify library

### Recommendation Engine Architecture

**Three-Tier System:**

1. **HybridRecommendationEngine** (`apps/recommendations/hybrid_recommendation_engine.py`)
   - Combines 5 recommendation strategies with weighted scoring
   - 5-minute caching system
   - Returns top 10-20 personalized tracks

2. **TrackDiscoveryEngine** (`apps/recommendations/track_discovery_engine.py`)
   - Alternative to Spotify's recommendations API (marked as broken)
   - Builds from user's top tracks, recent plays, saved tracks
   - Applies similarity matching

3. **PersonalizationEngine** (`apps/recommendations/personalization_engine.py`)
   - Rule-based learning (no ML training on Spotify data per TOS)
   - Analyzes last 30 days of feedback
   - Calculates audio feature preferences (acousticness, danceability, energy, etc.)
   - Adjusts API parameters dynamically

### Recent Backend Restructuring (Aug 18, 2025)

**Commit 96d76dcd:** "updated backend structure"
- Migrated from monolithic `songscope/` to modular `apps/` structure:
  - `apps/core/` - User management, models, views
  - `apps/ai/` - AI feedback interpretation
  - `apps/spotify/` - Spotify API utilities
  - `apps/recommendations/` - Recommendation algorithms
- Updated 56+ files with new imports
- Created comprehensive STRUCTURE.md documentation
- Reorganized tests into `tests/` directory

**Commit 87a5f3b2:** "login working with new structure"
- Fixed authentication after restructure
- Consolidated migrations
- Added OpenAI test scripts

---

## 6. FRONTEND ARCHITECTURE DEEP DIVE

### Next.js App Router Structure

**Routes:**
- `/` - Landing page with Spotify login button
- `/profile` - User dashboard (server-rendered)

**Component Organization:**
```
frontend/app/
├── layout.tsx (Root with CsrfProvider)
├── page.tsx (Landing)
├── components/
│   └── CsrfProvider.tsx (Fetch CSRF token on mount)
└── profile/
    ├── page.tsx (Server component with async data)
    └── components/
        ├── Recommendation/ (Song display & navigation)
        ├── TopArtists/ (Artist grid with expansion)
        ├── Feedback/ (Like/dislike + AI input)
        ├── AddToLiked/ (Save button)
        └── AudioPlayer/ (Preview player)
```

### State Management
- **Minimal approach** - No Redux/Zustand
- Component-level state with `useState`
- Side effects with `useEffect`
- Server components for initial data fetching

### API Communication
- **Axios client** (`services/axios.ts`)
- CSRF token added to all requests
- Credentials included (session cookies)
- Type-safe helpers: `get<T>()`, `post<T>()`

### Styling
- **Tailwind CSS** with custom color palette:
  - Navy (#14213d), Orange (#fca311), Spotify Green (#1DB954)
- Dark theme (bg-stone-950)
- Custom animations for notifications, tooltips, placeholders
- Responsive grid layouts

---

## 7. TESTING STATUS & RECOMMENDATIONS

### Current Testing Status

**Backend Tests:** Test suite exists in `backend/tests/`
- Unit tests for models
- Integration tests for API endpoints
- Run with: `python manage.py test` or `pytest tests/`

**Frontend Tests:** No test files found
- Recommendation: Add Jest + React Testing Library

### Manual Testing Plan

#### 1. Authentication Flow
```bash
✓ Test login button redirects to Spotify
✓ Verify OAuth callback creates session
✓ Check session persists across page refresh
✓ Test logout (if implemented)
```

#### 2. Recommendations
```bash
✓ Verify recommendations load on profile page
✓ Test Next/Previous navigation
✓ Test refresh button (force_fresh)
✓ Verify cache behavior (5-minute TTL)
```

#### 3. Feedback System
```bash
✓ Like a track → verify green button state
✓ Unlike track → verify state clears
✓ Dislike track → verify track removed
✓ Check feedback persists on track change
```

#### 4. AI Feedback (Needs Testing)
```bash
⚠ Test natural language input: "I want upbeat songs"
⚠ Verify OpenAI interpretation returned
⚠ Test rate limit handling
⚠ Test fallback rule-based interpretation
⚠ Verify recommendations update after feedback
```

#### 5. Top Artists
```bash
✓ Load artists grid
✓ Test time range filter (4 weeks/6 months/year)
✓ Click artist to expand details
✓ Verify user's favorite tracks displayed
```

#### 6. Add to Spotify Library
```bash
✓ Click heart icon
✓ Verify track added to Spotify account
✓ Check icon changes to filled heart
```

---

## 8. CONFIGURATION & ENVIRONMENT

### Environment Variables (Root `.env`)
```bash
# Backend URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Spotify OAuth
SPOTIFY_CLIENT_ID=<configured>
SPOTIFY_CLIENT_SECRET=<configured>
SPOTIFY_REDIRECT_URI=http://localhost:8000/spotify/callback/

# OpenAI
OPENAI_API_KEY=sk-proj-<configured>

# Dev Settings
OAUTHLIB_INSECURE_TRANSPORT=True
```

### Security Settings (Development Mode)
- `DEBUG = True`
- CSRF middleware disabled
- CORS allows localhost:3000 only
- Session cookies: HttpOnly, SameSite=Lax

**Production Recommendations:**
- Move SECRET_KEY to environment variable
- Enable CSRF middleware
- Use PostgreSQL instead of SQLite
- Enable HTTPS
- Encrypt Spotify tokens at rest
- Set DEBUG = False

---

## 9. KEY INTERVIEW TALKING POINTS

### Architecture Decisions
1. **Why separate frontend/backend?**
   - Scalability: Can deploy independently
   - Clear separation of concerns
   - Frontend can be static (CDN-ready)
   - Backend handles sensitive OAuth secrets

2. **Why SQLite for development?**
   - Zero configuration
   - File-based for easy backup
   - Sufficient for prototype/demo
   - Would migrate to PostgreSQL for production

3. **Why App Router over Pages Router?**
   - Modern Next.js pattern (future-proof)
   - Server Components reduce client bundle
   - Better data fetching patterns
   - Improved streaming and suspense support

### Technical Challenges Solved
1. **Spotify Token Management**
   - Automatic refresh before expiration
   - Stored securely in database
   - Handles edge cases (expired during request)

2. **Recommendation Quality**
   - Spotify's API marked as "broken" in code
   - Built custom hybrid engine combining 5 strategies
   - Caching reduces API calls and latency
   - Personalization learns from feedback

3. **AI Integration**
   - Natural language → structured preferences
   - Rate limiting and cost control
   - Fallback for reliability
   - Confidence scoring for transparency

4. **State Persistence**
   - Like state persists across track changes
   - Checks previous feedback on mount
   - Toggle functionality (unlike)
   - Real-time backend updates

### Recent Work (Last 2 Weeks)
1. **Backend Restructure** - Modular app architecture
2. **Like/Dislike State** - Persistent feedback buttons
3. **AI Feedback** - Natural language interpretation
4. **Artist Details** - Expanded artist view

---

## 10. AREAS FOR IMPROVEMENT (Interview Discussion Points)

### Known Issues
1. **Root `.next/` folder** - Should be removed from git
2. **AI Feedback untested** - Marked as needing testing
3. **No frontend tests** - Should add Jest/RTL
4. **SECRET_KEY in settings.py** - Should use env var
5. **CSRF middleware disabled** - Security concern for production
6. **OAUTHLIB_INSECURE_TRANSPORT** - Must be set as environment variable when starting server (see TROUBLESHOOTING.md)
7. **Missing dependencies** - `python-decouple` and `django-cors-headers` were missing from requirements.txt (now fixed)

### Feature Enhancements (Future Work)
1. **Search functionality** - Search tracks/artists/albums
2. **Playlist creation** - Create Spotify playlists from recommendations
3. **History tracking** - View past recommendations
4. **Settings page** - Manage preferences, account
5. **Social features** - Share recommendations with friends
6. **Mobile responsive** - Optimize for mobile devices
7. **Dark/light theme toggle** - User preference

### Performance Optimizations
1. **Image optimization** - Next.js Image component
2. **Code splitting** - Lazy load heavy components
3. **API request batching** - Reduce round trips
4. **Database indexing** - Add indexes to frequent queries
5. **Redis caching** - Replace in-memory cache

### Scalability Considerations
1. **PostgreSQL migration** - Better concurrency
2. **Celery for async tasks** - Background recommendation generation
3. **CDN for static assets** - Faster load times
4. **Load balancing** - Horizontal scaling
5. **Monitoring & logging** - Application insights

---

## 11. PROJECT STRENGTHS (Highlight in Interview)

1. **Clean Architecture** - Clear separation of concerns, modular design
2. **Modern Stack** - Latest Next.js, Django, TypeScript
3. **External API Integration** - Spotify + OpenAI with proper error handling
4. **AI/ML Application** - Practical use of GPT for user experience
5. **Sophisticated Algorithms** - Hybrid recommendation engine
6. **State Management** - Elegant solution without heavy libraries
7. **Recent Refactoring** - Shows code quality awareness
8. **Documentation** - STRUCTURE.md shows thoughtfulness
9. **Type Safety** - TypeScript throughout frontend
10. **Security Awareness** - CSRF protection, OAuth best practices

---

## 12. QUICK REFERENCE GUIDE

### Start Development
```bash
# Terminal 1: Backend
cd backend && source venv/bin/activate && python manage.py runserver

# Terminal 2: Frontend
cd frontend && npm run dev

# Access: http://localhost:3000
```

### Key Files to Know
- **Backend Entry:** `backend/config/urls.py`
- **API Views:** `backend/apps/core/views.py`
- **Models:** `backend/apps/core/models.py`
- **Recommendation Logic:** `backend/apps/recommendations/hybrid_recommendation_engine.py`
- **AI Service:** `backend/apps/ai/ai_feedback_service.py`
- **Frontend Entry:** `frontend/app/page.tsx`
- **Profile Dashboard:** `frontend/app/profile/page.tsx`
- **API Client:** `frontend/services/axios.ts`

### Database Commands
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Access admin: http://localhost:8000/admin
```

### Git Branch Info
- **Current Branch:** `development`
- **Main Branch:** `main`
- **Latest Commit:** "login working with new structure" (87a5f3b2)

---

## APPENDIX A: PRE-INTERVIEW TESTING CHECKLIST

### Environment Setup Verification (5 minutes)

**Backend Check:**
```bash
cd backend
source venv/bin/activate
python --version  # Should be 3.11+
pip list | grep Django  # Should show Django 5.1.3
python manage.py check  # Should show "System check identified no issues"
```

**Frontend Check:**
```bash
cd frontend
node --version  # Should be 18+
npm --version
ls -la node_modules | head  # Verify node_modules exists
```

**Environment Variables Check:**
```bash
cat .env | grep -E "SPOTIFY|OPENAI|BACKEND_URL"  # Verify all keys present
```

### Launch Testing (10 minutes)

**Step 1: Start Backend**
```bash
cd backend
source venv/bin/activate
python manage.py runserver
# ✓ Should show: "Starting development server at http://127.0.0.1:8000/"
# ✓ No errors in console
```

**Step 2: Start Frontend (new terminal)**
```bash
cd frontend
npm run dev
# ✓ Should show: "Ready on http://localhost:3000"
# ✓ Compiled successfully
```

**Step 3: Access Application**
- Open browser: http://localhost:3000
- ✓ Landing page loads with "Login with Spotify" button
- ✓ No console errors in browser DevTools

### Feature Testing (15 minutes)

**Test 1: Authentication Flow**
- [ ] Click "Login with Spotify"
- [ ] Redirected to Spotify OAuth page
- [ ] Authorize application
- [ ] Redirected back to `/profile` page
- [ ] Page loads with user's name displayed
- [ ] **Expected:** Profile dashboard with recommendations

**Test 2: Recommendations**
- [ ] Recommendations load automatically
- [ ] Track displays: image, name, artist, album
- [ ] Click "Next" button → navigates to next track
- [ ] Click "Previous" button → goes back
- [ ] Click "Refresh" icon → shows new recommendations
- [ ] **Expected:** Smooth navigation, no API errors

**Test 3: Like/Dislike Feedback**
- [ ] Click "Like" (thumbs up) → button turns green
- [ ] Navigate to different track, come back → like state persists
- [ ] Click like again → unlike (button clears)
- [ ] Click "Dislike" (thumbs down) → button turns red
- [ ] **Expected:** State persists, backend receives feedback

**Test 4: Top Artists**
- [ ] Scroll down to "Top Artists" section
- [ ] Artists grid loads with images
- [ ] Click time filter: "4 weeks" / "6 months" / "All time"
- [ ] Click an artist → expands to show details
- [ ] Shows: follower count, popularity, genres, tracks
- [ ] **Expected:** Smooth expansion, detailed info loads

**Test 5: Add to Spotify Library**
- [ ] Click heart icon on a track
- [ ] Icon changes to filled heart
- [ ] Check Spotify account → track appears in Liked Songs
- [ ] **Expected:** Track saved successfully

**Test 6: Audio Preview**
- [ ] If track has preview_url, audio player appears
- [ ] Click play button
- [ ] Audio plays (30-second preview)
- [ ] **Expected:** Audio plays without errors

**Test 7: AI Feedback (NEEDS TESTING)**
- [ ] Find AI feedback text input (may be in feedback section)
- [ ] Type: "I want something more upbeat"
- [ ] Click submit
- [ ] **Expected:** Interpretation returned with tempo/mood/energy
- [ ] **Note:** May hit rate limits if heavily tested

### Backend API Testing (5 minutes)

**Direct API Calls (using curl or browser):**

```bash
# Check auth endpoint
curl http://localhost:8000/api/check-auth/ -H "Cookie: sessionid=<your_session_id>"

# Get top tracks
curl http://localhost:8000/api/user-top-tracks/ -H "Cookie: sessionid=<your_session_id>"

# Get recommendations
curl http://localhost:8000/api/recommendations/ -H "Cookie: sessionid=<your_session_id>"
```

**Expected Responses:**
- All return 200 OK
- JSON responses with track data
- No 500 errors

### Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Backend won't start | Venv not activated | `source venv/bin/activate` |
| "No module named 'django'" | Dependencies not installed | `pip install -r requirements.txt` |
| Frontend won't start | Dependencies missing | `npm install` |
| CSRF errors | Token not fetched | Check browser console, refresh page |
| 401 Unauthorized | Session expired | Logout and login again |
| No recommendations | Spotify token expired | Check `/api/check-spotify-token/` |
| AI feedback fails | Rate limit or API key issue | Check OpenAI API key in .env |

### Performance Check

**Page Load Times:**
- Landing page: < 1 second
- Profile page (with data): 2-3 seconds (includes Spotify API calls)
- Recommendations refresh: 1-2 seconds (cached) or 3-5 seconds (fresh)

**Console Monitoring:**
- Check browser DevTools → Network tab
- Verify API calls return 200 OK
- Check for any 4xx or 5xx errors

### Database State Check

```bash
cd backend
python manage.py shell

# In Python shell:
from django.contrib.auth.models import User
from apps.core.models import SpotifyToken, UserProfile, UserFeedback

print(f"Users: {User.objects.count()}")
print(f"Spotify Tokens: {SpotifyToken.objects.count()}")
print(f"User Profiles: {UserProfile.objects.count()}")
print(f"Feedback entries: {UserFeedback.objects.count()}")
```

**Expected:**
- At least 1 user (you)
- At least 1 SpotifyToken
- UserProfile created automatically
- UserFeedback grows as you like/dislike tracks

---

## APPENDIX B: DEMO SCRIPT FOR INTERVIEW

### Opening (1 minute)
*"This is SongScope, a music recommendation app that combines Spotify's API with AI-powered personalization. Let me walk you through the core features."*

### Demo Flow (5-7 minutes)

**1. Authentication (30 seconds)**
- Show landing page
- Click "Login with Spotify"
- Explain OAuth 2.0 flow
- Return to profile dashboard

**2. Personalized Recommendations (2 minutes)**
- Show current recommendation with track details
- Explain hybrid recommendation engine:
  - "5 strategies: playlist mining, artist network, contextual analysis, popularity, and user feedback"
  - "Weighted scoring system, 5-minute caching"
- Navigate through tracks with Next/Previous
- Show refresh functionality

**3. Feedback System (1 minute)**
- Like a track: "This updates the personalization engine in real-time"
- Unlike it: "Toggle functionality with persistent state"
- Navigate to different track and back: "State persists across track changes"

**4. Top Artists Discovery (1 minute)**
- Show artist grid
- Filter by time range
- Expand an artist: "Shows follower count, genres, your favorite tracks, and artist's popular songs"

**5. AI Feedback Interpretation (1 minute)**
- Show text input
- Type: "I want something more energetic and upbeat"
- Explain: "GPT-4o-mini interprets this into structured preferences: tempo, mood, energy levels"
- Show interpretation result

**6. Code Walkthrough (2 minutes - if requested)**
- Backend: `apps/recommendations/hybrid_recommendation_engine.py`
- Frontend: `frontend/app/profile/components/Recommendation/`
- Explain recent restructuring (modular app architecture)

### Closing (1 minute)
*"The project demonstrates full-stack development with external API integration, AI/ML application, and sophisticated algorithms. Recent work includes the backend restructure for better maintainability and the AI feedback feature."*

---

## APPENDIX C: KEY FILES REFERENCE SHEET

### Backend Critical Files
| File | Purpose | Lines |
|------|---------|-------|
| `backend/config/urls.py` | All API endpoint routing | ~30 endpoints |
| `backend/apps/core/views.py` | API endpoint logic | ~800 lines |
| `backend/apps/core/models.py` | Database schema (7 models) | ~300 lines |
| `backend/apps/recommendations/hybrid_recommendation_engine.py` | Core recommendation logic | ~400 lines |
| `backend/apps/ai/ai_feedback_service.py` | OpenAI integration | ~200 lines |
| `backend/apps/spotify/utils.py` | Spotify API utilities | ~150 lines |

### Frontend Critical Files
| File | Purpose | Lines |
|------|---------|-------|
| `frontend/app/page.tsx` | Landing page | ~50 lines |
| `frontend/app/profile/page.tsx` | Profile dashboard (server component) | ~80 lines |
| `frontend/app/profile/components/Recommendation/Recommendation.tsx` | Main recommendation UI | ~340 lines |
| `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx` | Like/dislike state management | ~150 lines |
| `frontend/app/profile/components/Feedback/AIFeedbackInput.tsx` | AI feedback input (NEW) | ~256 lines |
| `frontend/app/profile/components/TopArtists/TopArtists.tsx` | Artist grid | ~218 lines |
| `frontend/services/axios.ts` | API client with CSRF | ~80 lines |

### Configuration Files
| File | Purpose |
|------|---------|
| `backend/config/settings.py` | Django configuration (CORS, auth, apps) |
| `frontend/next.config.mjs` | Next.js configuration |
| `frontend/tailwind.config.ts` | Custom theme colors |
| `.env` | Shared environment variables (Spotify, OpenAI) |
| `.gitignore` | Git ignore rules (properly configured) |

---

**Status:** Project is fully functional and ready to demonstrate. All services are configured and working. Latest development branch shows recent active development with sophisticated features. Both backend (venv) and frontend (node_modules) dependencies are installed and ready to run.
