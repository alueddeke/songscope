# Spotify Developer Dashboard Setup - URGENT

## The Problem

You're getting this error:
```
GET https://accounts.spotify.com/authorize?... 400 (Bad Request)
redirect_uri: Insecure
```

This means **your redirect URI is NOT registered** in Spotify Developer Dashboard.

---

## Solution: Add Redirect URI to Spotify Dashboard

### Step 1: Access Spotify Developer Dashboard

1. Open your browser
2. Go to: **https://developer.spotify.com/dashboard**
3. Log in with your Spotify account

### Step 2: Find Your App

Your app details:
- **Client ID:** `6bf1a7e2b72e4e36be9179772e15fe35`
- Look for an app with this Client ID in the dashboard

### Step 3: Edit Settings

1. Click on your app name
2. Click **"Settings"** or **"Edit Settings"** button (top right)
3. Scroll down to find **"Redirect URIs"** section

### Step 4: Add the Redirect URI

In the "Redirect URIs" section:

1. Find the text input box
2. Type **EXACTLY** (copy/paste recommended):
   ```
   http://localhost:8000/spotify/callback/
   ```
3. Click the **"ADD"** button
4. **IMPORTANT:** Click **"SAVE"** at the bottom of the page

### Step 5: Verify

After saving, you should see in the Redirect URIs list:
```
http://localhost:8000/spotify/callback/
```

⚠️ **CRITICAL:** Make sure it includes:
- `http://` (NOT https://)
- `localhost:8000` (port 8000, NOT 3000)
- `/spotify/callback/` (with trailing slash)

---

## Testing After Setup

### Wait for Propagation
Wait **1-2 minutes** for Spotify to propagate the changes.

### Restart Your Servers

**Terminal 1 - Backend:**
```bash
# Kill existing server first
kill $(lsof -ti:8000)

# Start fresh
cd backend
source venv/bin/activate
export OAUTHLIB_INSECURE_TRANSPORT=1
python manage.py runserver
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Test the Login Flow

1. Open browser to: http://localhost:3000
2. Click "Login with Spotify" button
3. **Expected:** Redirects to Spotify authorization page (NO 400 error!)
4. Click "Authorize" on Spotify page
5. **Expected:** Redirects back to http://localhost:3000/profile

---

## Troubleshooting

### Still Getting 400 Error?

**Check These:**

1. **Is the URI exact?**
   - Must be: `http://localhost:8000/spotify/callback/`
   - Common mistake: Missing trailing `/`
   - Common mistake: Wrong port (3000 instead of 8000)

2. **Did you click Save?**
   - After clicking "Add", you MUST click "Save" at the bottom

3. **Did you wait?**
   - Changes can take 1-2 minutes to propagate
   - Try clearing your browser cache

4. **Is the backend running?**
   ```bash
   curl -I http://localhost:8000/spotify-login/
   # Should show: HTTP/1.1 302 Found
   ```

5. **Is environment variable set?**
   ```bash
   echo $OAUTHLIB_INSECURE_TRANSPORT
   # Should show: 1
   ```

### Alternative: Check Spotify Dashboard via API

Run this command to verify your setup:
```bash
cd backend
source venv/bin/activate
python check_spotify_config.py
```

This will show you exactly what to configure.

---

## What if Spotify Doesn't Allow HTTP?

If Spotify has completely blocked HTTP redirect URIs (unlikely for localhost), you'll need to:

1. **Use a different redirect URI pattern** that Spotify allows
2. **Set up HTTPS locally** with self-signed certificates
3. **Use Spotify's recommended development flow**

Contact Spotify Support if HTTP localhost URLs are blocked.

---

## Summary Checklist

- [ ] Logged into https://developer.spotify.com/dashboard
- [ ] Found app with Client ID: `6bf1a7e2b72e4e36be9179772e15fe35`
- [ ] Clicked "Settings"
- [ ] Added redirect URI: `http://localhost:8000/spotify/callback/`
- [ ] Clicked "ADD"
- [ ] Clicked "SAVE"
- [ ] Waited 1-2 minutes
- [ ] Restarted backend server with `export OAUTHLIB_INSECURE_TRANSPORT=1`
- [ ] Tested login flow - should work!

---

**Once you complete these steps, the OAuth error will be fixed!**
