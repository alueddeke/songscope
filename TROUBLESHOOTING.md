# SongScope - Troubleshooting Guide & Known Issues

**Last Updated:** March 18, 2026

This document tracks all discovered issues, their solutions, and system-specific configurations for the SongScope project.

---

## Table of Contents
1. [Environment Setup Issues](#environment-setup-issues)
2. [Backend Issues](#backend-issues)
3. [Frontend Issues](#frontend-issues)
4. [Spotify OAuth Issues](#spotify-oauth-issues)
5. [Quick Reference Commands](#quick-reference-commands)

---

## Environment Setup Issues

### Issue 1: Virtual Environment Uses Anaconda Python

**Problem:** The `backend/venv` is linked to Anaconda Python instead of standard Python virtualenv.

**Detection:**
```bash
source venv/bin/activate
which python
# Returns: /opt/anaconda3/bin/python
```

**Impact:**
- Packages installed globally in Anaconda are available in venv
- Not a true isolated environment
- Works fine for development but less portable

**Solution:**
- Current setup is functional - no action needed
- For production: Create true isolated venv with `python -m venv venv` (not conda)

**Status:** ✓ Working as-is

---

## Backend Issues

### Issue 2: Missing Dependencies in requirements.txt

**Problem:** `backend/requirements.txt` was missing critical dependencies that `config/settings.py` requires.

**Missing Packages:**
- `python-decouple` - Used for loading environment variables
- `django-cors-headers` - Required for CORS configuration

**Symptoms:**
- Import errors when starting Django
- Server fails to start silently
- Multiple zombie processes on port 8000
- All endpoints return 404

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install python-decouple django-cors-headers
```

**Updated requirements.txt:**
```
Django==5.1.3
djangorestframework==3.15.2
django-cors-headers==4.3.1
spotipy==2.23.0
requests==2.31.0
python-decouple==3.8
openai==1.99.9
```

**Status:** ✓ Fixed

---

### Issue 3: Zombie Processes on Port 8000

**Problem:** Multiple failed Django server attempts leave processes running on port 8000, preventing new server from starting.

**Detection:**
```bash
lsof -ti:8000
# Returns multiple process IDs if issue exists
```

**Symptoms:**
- "Port already in use" error
- Server appears to be running but returns 404 for all endpoints
- Cannot start new server instance

**Solution:**
```bash
# Kill all processes on port 8000
kill $(lsof -ti:8000)

# Or kill specific process
kill <PID>

# Then restart server
cd backend
source venv/bin/activate
python manage.py runserver
```

**Prevention:** Always properly stop the server with Ctrl+C instead of closing terminal

**Status:** ✓ Fixed

---

## Spotify OAuth Issues

### Issue 4: OAuth "redirect_uri: Insecure" Error (400 Bad Request)

**Problem:** Spotify OAuth rejects the authorization request with "redirect_uri: Insecure" error because HTTP (not HTTPS) is being used in development.

**Error Details:**
```
GET https://accounts.spotify.com/authorize?response_type=code&client_id=...
400 (Bad Request)
Error: redirect_uri: Insecure
```

**Root Cause:**
- OAuth library (requests-oauthlib) enforces HTTPS by default
- Development uses HTTP (localhost:8000)
- Environment variable `OAUTHLIB_INSECURE_TRANSPORT` must be set BEFORE any OAuth code runs

**Solution:**

**Step 1:** Verify `.env` file has the setting:
```bash
# In /Users/antonilueddeke/Desktop/Projects/songscope/.env
OAUTHLIB_INSECURE_TRANSPORT=1
```

**Step 2:** Ensure `config/settings.py` reads this setting:
```python
# Line 16 in backend/config/settings.py
OAUTHLIB_INSECURE_TRANSPORT = config('OAUTHLIB_INSECURE_TRANSPORT', 'False').lower() == 'true'
```

**Step 3:** Ensure `apps/core/views.py` sets environment variable early:
```python
# Line 41-42 in backend/apps/core/views.py
if settings.OAUTHLIB_INSECURE_TRANSPORT:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
```

**Step 4:** The fix is now permanently applied in the code!

The file `backend/apps/core/views.py` now sets `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'` at the very top, BEFORE importing `requests_oauthlib`. This ensures the OAuth library allows HTTP redirect URIs for local development.

**You no longer need to manually set the environment variable!** Just start the server normally:
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

**Testing:**
1. Go to http://localhost:3000
2. Click "Login with Spotify"
3. Should redirect to Spotify authorization page (NOT show 400 error)
4. Authorize app
5. Should redirect back to http://localhost:3000/profile

**Status:** ✓ PERMANENTLY FIXED - Environment variable now set at module import time in views.py

**Production Note:** This setting should NEVER be enabled in production. Use HTTPS with valid SSL certificates.

---

### Issue 5: Spotify Developer Dashboard Configuration - CRITICAL

**Problem:** Spotify OAuth returns "redirect_uri: Insecure" 400 error even with `OAUTHLIB_INSECURE_TRANSPORT=1` set.

**Root Cause:** The redirect URI `http://localhost:8000/spotify/callback/` is NOT registered in your Spotify Developer Dashboard.

**Solution - YOU MUST DO THIS:**

1. Go to https://developer.spotify.com/dashboard
2. Log in with your Spotify account
3. Select your app (Client ID: `6bf1a7e2b72e4e36be9179772e15fe35`)
4. Click "Settings" (or "Edit Settings")
5. Scroll to "Redirect URIs" section
6. Add this EXACT URI (including trailing slash):
   ```
   http://localhost:8000/spotify/callback/
   ```
7. Click "Add"
8. Click "Save" at the bottom
9. Wait 1-2 minutes for changes to propagate

**Common Mistakes:**
- Missing trailing slash: `http://localhost:8000/spotify/callback` (WRONG - must have /)
- Wrong port: `http://localhost:3000/spotify/callback/` (WRONG - must be 8000)
- HTTPS in development: `https://localhost:8000/spotify/callback/` (WRONG - must be http for local)
- Wrong path: `http://localhost:8000/callback/` (WRONG - must be /spotify/callback/)

**Verification After Adding:**
1. Restart both frontend and backend servers
2. Go to http://localhost:3000
3. Click "Login with Spotify"
4. Should redirect to Spotify authorization page (NOT 400 error)
5. Authorize app
6. Should redirect back to your app successfully

**Alternative Solution (If HTTP Not Allowed):**

If Spotify has blocked HTTP redirect URIs entirely, you'll need to use HTTPS locally:

1. Generate SSL certificates for localhost
2. Update `.env` to use `https://localhost:8000/spotify/callback/`
3. Configure Django to use SSL
4. Configure Next.js to use SSL
5. Add HTTPS URI to Spotify Dashboard

**Status:** ⚠️ ACTION REQUIRED - Check Spotify Dashboard NOW

---

## Frontend Issues

### Issue 6: CSRF Token Issues

**Problem:** Frontend requests may fail with 403 Forbidden due to missing CSRF token.

**Detection:**
- Browser console shows "403 Forbidden" on API requests
- Error message mentions CSRF verification failed

**Solution:**
- Frontend has `CsrfProvider` component that fetches token on mount
- Ensure this component wraps your app in `app/layout.tsx`
- Axios client automatically includes CSRF token in headers

**Verification:**
```javascript
// In browser console:
document.cookie
// Should see: csrftoken=<value>
```

**Status:** ✓ Working (configured in frontend)

---

## Quick Reference Commands

### Start Both Servers

**Terminal 1 - Backend:**
```bash
cd /Users/antonilueddeke/Desktop/Projects/songscope/backend
source venv/bin/activate
export OAUTHLIB_INSECURE_TRANSPORT=1
python manage.py runserver
```

**Terminal 2 - Frontend:**
```bash
cd /Users/antonilueddeke/Desktop/Projects/songscope/frontend
npm run dev
```

### Check If Servers Are Running

```bash
# Check backend
curl -I http://localhost:8000/api/csrf-token/

# Check frontend
curl -I http://localhost:3000

# Check what's using port 8000
lsof -ti:8000
```

### Kill Zombie Processes

```bash
# Backend (port 8000)
kill $(lsof -ti:8000)

# Frontend (port 3000)
kill $(lsof -ti:3000)
```

### Verify Django Configuration

```bash
cd backend
source venv/bin/activate
python manage.py check
# Should output: System check identified no issues (0 silenced).
```

### Test Spotify OAuth Redirect

```bash
# Should return 302 redirect to Spotify
curl -I http://localhost:8000/spotify-login/
```

### View Server Logs

If running in background, use Claude Code's `/tasks` command to see running background shells and their output.

---

## Environment-Specific Notes

### Your System Configuration
- **OS:** macOS (Darwin 24.6.0)
- **Python:** 3.11.7 (via Anaconda)
- **Node:** 18+
- **Working Directory:** `/Users/antonilueddeke/Desktop/Projects/songscope`
- **Git Branch:** `development` (main branch: `main`)
- **Virtual Env:** Uses Anaconda Python (not standard venv)

### Critical Environment Variables
```bash
# Root .env file location:
/Users/antonilueddeke/Desktop/Projects/songscope/.env

# Required variables:
SPOTIFY_CLIENT_ID=6bf1a7e2b72e4e36be9179772e15fe35
SPOTIFY_CLIENT_SECRET=4f0d1b7c78cd40acaefc14c293161f49
SPOTIFY_REDIRECT_URI=http://localhost:8000/spotify/callback/
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
OAUTHLIB_INSECURE_TRANSPORT=1
OPENAI_API_KEY=sk-proj-...
```

---

## Known Working Configuration

**Last Verified:** March 18, 2026 at 18:58 UTC

**Working Setup:**
- Backend running on http://localhost:8000
- Frontend running on http://localhost:3000
- Spotify OAuth redirects working
- CSRF tokens generating correctly
- All API endpoints responding

**Test Results:**
```bash
✓ GET /api/csrf-token/ → 200 OK
✓ GET /spotify-login/ → 302 to Spotify
✓ Server logs show successful requests
```

---

## Future Improvements Needed

1. **Virtual Environment:** Migrate from Anaconda venv to standard Python venv for better portability
2. **Root .next Folder:** Remove stale build artifacts from git (see PROJECT_AUDIT_INTERVIEW_GUIDE.md)
3. **Environment Variable Loading:** Consider consolidating python-decouple and python-dotenv usage
4. **Production Deployment:** Document HTTPS setup and disable OAUTHLIB_INSECURE_TRANSPORT
5. **Testing:** Add automated integration tests for OAuth flow
6. **Documentation:** Keep this file updated as new issues are discovered

---

## Getting Help

If you encounter new issues:

1. Check this document first
2. Check `PROJECT_AUDIT_INTERVIEW_GUIDE.md` for architecture details
3. Check server logs:
   - Backend: Look at terminal running `python manage.py runserver`
   - Frontend: Look at terminal running `npm run dev`
   - Browser: Check DevTools console and Network tab
4. Verify environment variables are loaded: `echo $OAUTHLIB_INSECURE_TRANSPORT`
5. Restart both servers with a clean slate (kill all processes first)

---

**Document Status:** Living document - update as issues are discovered and resolved.
