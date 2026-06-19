# SongScope — Current State
_Updated 2026-06-19 session 2_

## Status: WORKING ✓

All critical features functional after this session's fixes.

---

## How to Launch

**Terminal 1 — Django backend (port 8000):**
```bash
cd ~/Desktop/Projects/songscope/backend
source venv/bin/activate
python manage.py runserver
```

**Terminal 2 — Next.js frontend (port 3000):**
```bash
cd ~/Desktop/Projects/songscope/frontend
npm run dev
```

**Port conflicts:**
- `maple_key` Docker container binds `0.0.0.0:8000` — stop it first
- Other Next.js projects may occupy port 3000 → `lsof -i :3000` to check

---

## What Works

- Spotify OAuth login ✓
- Profile page loads with username ✓
- **DailyGem component** renders (was swapped in this session — replaces old Recommendation carousel) ✓
- Score bars (Genre Match / Novelty / Feedback) visible ✓
- Explanation text visible ✓
- Album art loads (Spotify CDN `i.scdn.co` added to next.config.mjs) ✓
- Feedback buttons (like/dislike) ✓
- Add to Liked ✓
- **AI text feedback (OpenAI)** ✓ — fixed this session
- "Find me another song" button appears after dislike OR AI feedback ✓
- "Generate new gem" generates a truly different song ✓ — fixed this session
- MetricsStrip, LikeTrendChart, TasteProfileChart, DiversityScore, TopArtists ✓

---

## Bugs Fixed This Session

### 1. DailyGem not mounted
`profile/page.tsx` imported `Recommendation` instead of `DailyGem`.
**Fix:** Swapped import + JSX tag.

### 2. Spotify image 403 (next/image)
`i.scdn.co` not in `next.config.mjs` `remotePatterns`.
**Fix:** Added `i.scdn.co` to remotePatterns.

### 3. AI feedback 403 CSRF error
DRF's `SessionAuthentication.enforce_csrf()` runs its own CsrfViewMiddleware check
that ignores Django's `CSRF_TRUSTED_ORIGINS`. Cross-port localhost (3000→8000)
triggers the failure.
**Fix:** `config/auth.py` — `CsrfExemptSessionAuthentication` subclasses
`SessionAuthentication` and overrides `enforce_csrf` to no-op. CORS config
already enforces origin restrictions. Settings updated in `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`.

### 4. AI feedback returned fallback (confidence 0.3) instead of real interpretation
OpenAI prompt did not include `response_format={"type": "json_object"}`, so model
returned empty/markdown-wrapped content. `json.loads("")` failed silently, fell
back to dumb keyword matching.
**Fix:** Added `response_format={"type": "json_object"}` to `openai_client.chat.completions.create()`.
Now returns structured interpretation (confidence ~0.8, specific_genres populated).

### 5. "Generate new gem" returned same cached song
`force_new=true` delete logic was inside the Fresh branch, AFTER the Cached branch
early-return. Cached gem was returned before deletion ran.
**Fix:** Moved `force_new` check and `DailyGem.objects.filter(...).delete()` to
the top of the view, before the Cached branch. Cached branch now skipped when
`force_new=true`.

### 6. Track lookup 400 in submit_ai_feedback
Used `Track.objects.get(spotify_id=...)` — raises DoesNotExist if track not yet
in DB → 400 → frontend shows generic error.
**Fix:** Changed to `Track.objects.get_or_create(...)`.

---

## Architecture Reference

- Backend: Django 5.2.5 + DRF, SQLite, `backend/apps/core/views.py`
- Frontend: Next.js 13+ App Router, `frontend/app/profile/`
- Auth: `config/auth.py` → `CsrfExemptSessionAuthentication`
- OpenAI: `backend/apps/ai/ai_feedback_service.py`, `gpt-4o-mini`, `response_format=json_object`

### Key backend endpoints
| Endpoint | View | Notes |
|---|---|---|
| `GET /api/daily-gem/` | `get_daily_gem` | `?force_new=true` deletes today's gem + regenerates |
| `POST /api/submit-ai-feedback/` | `submit_ai_feedback` | OpenAI interprets NL feedback |
| `POST /api/submit-feedback/` | `submit_feedback` | like/dislike |
| `GET /api/recommendation-metrics/` | `get_recommendation_metrics` | MetricsStrip data |
| `GET /api/recommendation-trend/` | `get_recommendation_trend` | LikeTrendChart data |
| `POST /api/add-track-to-liked/` | `add_track_to_liked` | Spotify save + was_saved |

### Key frontend files changed this session
| File | Change |
|---|---|
| `frontend/app/profile/page.tsx` | Swapped Recommendation → DailyGem |
| `frontend/next.config.mjs` | Added `i.scdn.co` to remotePatterns |
| `frontend/app/profile/components/DailyGem/DailyGem.tsx` | `showNewGemPrompt` state, passes `onDislike`/`onFeedbackSubmitted` callbacks |
| `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx` | Added `onDislike` callback prop |
| `backend/config/auth.py` | NEW — `CsrfExemptSessionAuthentication` |
| `backend/config/settings.py` | DRF auth class updated |
| `backend/apps/ai/ai_feedback_service.py` | `response_format=json_object` |
| `backend/apps/core/views.py` | `force_new` fix, `get_or_create` for track |

---

## Remaining / Next Steps

- No known broken features as of end of session 2
- Portfolio is functionally complete for demo
- Consider: commit all session 2 changes before next session
