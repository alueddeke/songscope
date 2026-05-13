# Technology Stack — v1.1 Explainability + Compound Success Metric

**Project:** SongScope
**Milestone:** v1.1 — "Why this gem" score breakdown + compound success metric
**Researched:** 2026-05-13
**Confidence:** HIGH — based on direct codebase inspection + Spotify API changelog verification

---

## What Already Exists (Do Not Re-add)

These are confirmed present in the codebase. No new dependencies required for these.

| Component | Status | Location |
|-----------|--------|----------|
| `score_breakdown` dict | Already computed per-recommendation in `_score_recommendations()` — `{genre_sim, novelty, feedback_multiplier, source}` | `hybrid_recommendation_engine.py:875-880` |
| `score_breakdown` in API response | Already returned by `get_daily_gem` fresh branch via `gem_data.get('score_breakdown', {})` | `views.py:1139` |
| `score_breakdown: {}` in cached branch | Exists but returns empty dict — cached gems lose the breakdown | `views.py:1060, 1123` |
| `explanation` field | `DailyGem.explanation` DB column exists (TextField, blank=True); always `''` currently | `models.py:285`, `views.py:1101` |
| `DailyGem.was_liked` | Exists, written on LIKE/DISLIKE/unlike | `models.py:289` |
| `DailyGem.was_skipped` | Exists (BooleanField, default=False), never written to | `models.py:290` |
| `user-library-read` scope | Already in OAuth scope string | `views.py:48` |
| `user-read-playback-state` scope | Already in OAuth scope string | `views.py:41` |
| `sp.current_user_saved_tracks_contains()` | Present in spotipy 2.25.1 | `venv/spotipy/client.py:1328` |
| Recharts | Installed (`^3.8.1`) | `package.json` |
| Tailwind CSS | Installed (`^3.4.1`) | `package.json` |
| lucide-react | Installed (`^0.454.0`) | `package.json` |
| Django 5.1.3 / DRF 3.15.2 | Installed | `requirements.txt` |
| `JSONField` support | SQLite supports Django JSONField since Django 3.1 | Django built-in |

---

## What Needs Adding

### 1. Score Breakdown Persistence (Backend)

**Problem:** `score_breakdown` is computed at scoring time and passed through in-memory on the fresh branch, but it is never written to the DB. The cached branch returns `{}`. After day 1, every gem returns an empty breakdown.

**Solution:** Add a `score_breakdown` JSONField to `DailyGem`. Write it at gem creation time. Return it from both branches of `get_daily_gem`.

**Changes required:**
- `DailyGem` model: add `score_breakdown = models.JSONField(default=dict, blank=True)`
- New migration: `0008_dailygem_score_breakdown.py`
- `get_daily_gem` view, fresh branch: pass `score_breakdown=gem_data.get('score_breakdown', {})` into `DailyGem.objects.get_or_create(defaults={...})`
- `get_daily_gem` view, cached branch: return `gem.score_breakdown` instead of `{}`

**No new dependencies.** Django's `JSONField` is built-in (SQLite-compatible since Django 3.1). Confirmed: project uses Django 5.1.3.

**Confidence:** HIGH — direct codebase inspection.

---

### 2. Compound Success Metric (Backend)

**Goal:** Binary hit = track was saved (liked in Spotify library) AND user gave LIKE feedback. Playback confirmation is not feasible (see Spotify API section below).

**What "saved" means here:** The user clicks the heart icon in the existing `add_track_to_liked` endpoint, which calls `sp.current_user_saved_tracks_add([track_id])`. This is a confirmed, user-initiated action — stronger signal than passive playback detection.

**Checking save status:** `sp.current_user_saved_tracks_contains([track_id])` — available in spotipy 2.25.1 and confirmed available for Dev Mode apps via the new `GET /me/library/contains` endpoint (February 2026 migration). The `user-library-read` scope is already in the OAuth scope string.

**Definition to implement:**
```
compound_hit = DailyGem.was_liked is True AND track was saved to Spotify library
```

**Changes required:**
- `DailyGem` model: add `was_saved = models.BooleanField(null=True, blank=True)` — null = unknown, True = confirmed saved
- New migration: included in `0008_dailygem_score_breakdown.py` or as `0009_dailygem_was_saved.py`
- `submit_feedback` view: when `feedback_type == 'LIKE'`, call `sp.current_user_saved_tracks_contains([track_id])` and write `gem.was_saved` if truthy (already has Spotify client in scope)
- `add_track_to_liked` view: on success, update `DailyGem.was_saved = True` for today's gem if track matches
- `get_recommendation_metrics` view: add `compound_hit_rate` to the response — `(gems where was_liked=True AND was_saved=True).count() / gem_total`

**No new dependencies.** `current_user_saved_tracks_contains` is in the existing spotipy install.

**Confidence:** HIGH — code paths confirmed in codebase; endpoint availability confirmed via Spotify Feb 2026 changelog.

---

### 3. "Why This Gem" Explanation Card (Frontend)

**Goal:** Small inline card below the track title in the `DailyGem` component showing score percentages: genre match %, novelty score, feedback multiplier contribution.

**What already exists:**
- `DailyGem.tsx` renders `explanation` (text) and `track.preview_url` (AudioPlayer) — the card slots in between or below
- Recharts is installed and used (LikeTrendChart) — available if a mini bar chart is wanted
- Tailwind is installed — all layout/color styling handled there
- lucide-react is installed — icons available without extra deps

**What needs adding:** A new `ScoreBreakdown` component or inline JSX in `DailyGem.tsx` that:
1. Reads `score_breakdown: { genre_sim, novelty, feedback_multiplier }` from the `get_daily_gem` response (already in the fresh-branch response; will be in the cached branch after the backend fix above)
2. Converts raw floats to percentages: `genre_sim * 100`, `novelty * 100`, `feedback_multiplier` (already 0.5–1.5 scale — display as a multiplier label, not %)
3. Renders three labelled bars or pill badges using Tailwind width utilities (e.g., `w-[{pct}%]`)

**Recharts vs. native Tailwind bars:** Recharts adds ~2KB gzipped per chart instance and requires a `ResponsiveContainer` wrapper. For three static bar segments, a Tailwind-native bar (a div with percentage width) is lighter, easier to test, and already the pattern in the codebase for simple data display. Use Recharts only if an animated or interactive chart is explicitly requested.

**No new dependencies.** Tailwind + lucide-react cover the entire UI need.

**Confidence:** HIGH — direct codebase inspection of component structure and installed packages.

---

### 4. Structured `explanation` Field from API (Optional Backend)

**Current state:** `DailyGem.explanation` is always `''`. The `get_daily_gem` view returns it verbatim.

**Options — in order of complexity:**

**Option A (zero deps, instant):** Generate explanation text deterministically from `score_breakdown` at gem creation time. Example template: `"Genre match: 82% — your taste for indie folk overlaps strongly. Novelty: 71% — popularity 18 suggests few listeners. Feedback: no prior signal."` Write to `DailyGem.explanation` at creation. Zero LLM cost, always available, fully reproducible.

**Option B (existing OpenAI integration):** Pass `score_breakdown` + track metadata to the existing `get_feedback_interpreter()` / OpenAI call. This already exists in `ai_feedback_service.py` and has a rate limiter. Only adds an additional OpenAI call per new gem per day — within the $1/day budget if the prompt is short (~100 tokens). Requires a new method on `AIFeedbackService` or a standalone prompt function. The explanation text is then stored in `DailyGem.explanation`.

**Recommendation:** Implement Option A first (no LLM cost, fully testable, guaranteed output). Add Option B as an upgrade path if richer natural-language explanations are wanted later.

**No new dependencies for either option.** OpenAI SDK already installed (`openai==1.99.9`).

**Confidence:** HIGH.

---

## Spotify API Status — Playback Tracking

This section documents what is and is not feasible for the compound success metric's "played" component.

### What Was Deprecated (confirmed)

| Endpoint / Scope | Status | Source |
|-----------------|--------|--------|
| `GET /v1/audio-features/{id}` | Removed November 2024 | Spotify blog 2024-11-27 |
| `GET /v1/recommendations` | Removed November 2024 | Spotify blog 2024-11-27 |
| `GET /v1/artists/{id}/related-artists` | Soft-deprecated; still callable, may return empty | Spotify blog 2024-11-27 |
| `GET /v1/me/player` (Get Playback State) | Still in Spotify docs, but **requires Spotify Premium** for the authenticated user AND the app must be in Extended Quota Mode or Premium-app status as of February 2026 changes | Spotify dev community 2026 |
| `GET /v1/me/player/currently-playing` | Same Premium + mode restrictions as above | Spotify dev community 2026 |

### What Is Still Available (confirmed)

| Endpoint | Scope Required | Use |
|----------|---------------|-----|
| `GET /me/tracks/contains` (legacy) or `GET /me/library/contains` (Feb 2026 replacement) | `user-library-read` | Check if track is saved |
| `GET /me/player/recently-played` | `user-read-recently-played` | Playback history (last 50 tracks, no timestamps precise enough for "did they play the gem today") |
| `POST /me/tracks` / `PUT /me/library` | `user-library-modify` | Save tracks (already used) |

### Practical Conclusion for Compound Metric

Real-time playback detection via `GET /v1/me/player/currently-playing` is unreliable for this project because: (1) it requires Spotify Premium on the user's account, (2) Dev Mode apps with fewer than 25 users face additional 403 errors after February 2026, and (3) it only tells you what is playing right now, not whether the gem was played at all today.

**Best available proxy for "played":** `current_user_recently_played` — check if the gem's track ID appears in the last 50 recently played items after the gem was created. This is a weak signal (the user may have played it from Spotify directly without the app) but it is the only non-Premium, non-deprecated proxy available.

**Recommended compound metric:** `was_saved = True` (user explicitly hearted the track via the app) AND `was_liked = True` (user gave LIKE feedback). "Saved" is stronger than "played" as a success signal — it represents explicit intent. Drop "played" from the compound definition given the API constraints. Document this decision and the reasoning for portfolio/interview purposes.

**Confidence:** MEDIUM — playback API behavior post-Feb-2026 is confirmed by community reports but not official changelog text (WebFetch to official docs was blocked). The `check_saved_tracks` availability is HIGH confidence from confirmed changelog notes.

---

## Dependency Summary

| Package | Version | Status | Purpose |
|---------|---------|--------|---------|
| Django JSONField | built-in Django 3.1+ | Already available | `score_breakdown` and future JSON fields on models |
| spotipy | 2.25.1 (installed) | Already installed | `current_user_saved_tracks_contains` for save-check |
| openai | 1.99.9 (installed) | Already installed | Optional: OpenAI-generated explanation text |
| Recharts | ^3.8.1 (installed) | Already installed, use sparingly | Score breakdown mini-chart if animated chart is wanted |
| Tailwind CSS | ^3.4.1 (installed) | Already installed | Score card layout, percentage bars |
| lucide-react | ^0.454.0 (installed) | Already installed | Icons in explanation card |

**New packages to install: none.**

---

## Migration Plan (Django)

Two new DB columns required. Can be one migration or two:

```python
# 0008_dailygem_score_breakdown_was_saved.py
class Migration(migrations.Migration):
    dependencies = [("core", "0007_spotifytoken_refresh_token_nullable")]
    operations = [
        migrations.AddField(
            model_name="dailygem",
            name="score_breakdown",
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.AddField(
            model_name="dailygem",
            name="was_saved",
            field=models.BooleanField(null=True, blank=True),
        ),
    ]
```

No data migration needed — both fields are nullable/have defaults. Existing rows get `{}` and `None` respectively.

---

## Integration Points with Existing Score Formula

The score formula `0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier` is LOCKED (confirmed in code comment). This milestone does not change it. Integration points:

| Existing Code | What v1.1 Adds |
|--------------|----------------|
| `_score_recommendations()` already writes `rec['score_breakdown']` | Write that dict to `DailyGem.score_breakdown` at creation — no changes to scoring logic |
| `get_daily_gem` fresh branch already reads `gem_data.get('score_breakdown', {})` | Pass it to `DailyGem` defaults dict |
| `get_daily_gem` cached branch returns `'score_breakdown': {}` | Change to return `gem.score_breakdown` |
| `submit_feedback` already has Spotify client and track | Add `sp.current_user_saved_tracks_contains([track_id])` call and write `gem.was_saved` |
| `add_track_to_liked` already calls `sp.current_user_saved_tracks_add` | On success, set `DailyGem.was_saved = True` for today's gem if track matches |
| `get_recommendation_metrics` already reads `DailyGem` fields | Add `compound_hit_rate` field using `was_liked=True` + `was_saved=True` |

---

## What NOT to Add

- **No new backend framework, ORM, or database.** SQLite + Django ORM handles all new fields trivially.
- **No Redis/Celery for async save-check.** The `current_user_saved_tracks_contains` call is fast (<100ms) and fits synchronously in the existing feedback view.
- **No new charting library.** Recharts is installed; Tailwind div-bars are sufficient for three-bar score card.
- **No GraphQL or separate API layer.** The existing DRF/JsonResponse pattern is sufficient for `score_breakdown`.
- **No real-time playback polling.** Premium requirement + Dev Mode restrictions make this unreliable. The `recently_played` endpoint exists as a soft fallback only.
- **No separate "explanation microservice."** The deterministic template approach in Option A is zero-infrastructure and fully testable.
- **No upgrade to spotipy 2.25.1.** It is already installed at that version. The `requirements.txt` lists `spotipy==2.23.0` — update the pin to `spotipy==2.25.1` to match the venv reality, but this is a housekeeping change, not a feature dependency.

---

## Sources

- [Spotify Web API Changelog — February 2026](https://developer.spotify.com/documentation/web-api/references/changes/february-2026)
- [Spotify February 2026 Migration Guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)
- [Introducing Changes to the Web API — November 2024](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)
- [Spotify Developer Community — February 2026 API changes thread](https://community.spotify.com/t5/Spotify-for-Developers/February-2026-Spotify-for-Developers-update-thread/td-p/7330564)
- [Spotify Developer Community — Player API 403 Premium Required 2026](https://community.spotify.com/t5/Spotify-for-Developers/403-Error-Active-Premium-Subscription-Required-Even-Though/td-p/7369809)
- Codebase: `backend/apps/recommendations/hybrid_recommendation_engine.py` — score formula and `score_breakdown` structure (direct inspection)
- Codebase: `backend/apps/core/models.py` — `DailyGem`, `RecommendationLog` field inventory (direct inspection)
- Codebase: `backend/apps/core/views.py` — `get_daily_gem`, `submit_feedback`, `add_track_to_liked` endpoint structure (direct inspection)
- Codebase: `frontend/package.json` — installed frontend deps (direct inspection)
