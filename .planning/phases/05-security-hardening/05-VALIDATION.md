---
phase: 05
slug: security-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-12
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | SECRET_KEY rotation | T-05-01 | `settings.SECRET_KEY` does not contain 'insecure' | smoke | `cd backend && python -c "import django; django.setup(); from django.conf import settings; assert 'insecure' not in settings.SECRET_KEY"` | ✅ | ⬜ pending |
| 05-01-02 | 01 | 1 | SECRET_KEY via decouple | T-05-01 | settings.py uses `config('SECRET_KEY')` not `os.environ.get` | source | `grep "config('SECRET_KEY')" backend/config/settings.py` | ✅ | ⬜ pending |
| 05-02-01 | 02 | 1 | CLIENT_SECRET removed | T-05-02 | next.config.mjs has no SPOTIFY_CLIENT_SECRET reference | source | `grep -v "SPOTIFY_CLIENT_SECRET" frontend/next.config.mjs` | ✅ | ⬜ pending |
| 05-02-02 | 02 | 1 | Frontend build passes | T-05-02 | `npm run build` exits 0 | smoke | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 05-03-01 | 03 | 2 | CSRF middleware enabled | T-05-03 | CsrfViewMiddleware uncommented in MIDDLEWARE list | source | `grep "CsrfViewMiddleware" backend/config/settings.py \| grep -v "#"` | ✅ | ⬜ pending |
| 05-03-02 | 03 | 2 | Dead class removed | T-05-03 | CsrfExemptSessionAuthentication not in views.py | source | `grep -c "CsrfExemptSessionAuthentication" backend/apps/core/views.py` outputs 0 | ✅ | ⬜ pending |
| 05-03-03 | 03 | 2 | All 77 tests still pass | T-05-03 | Full suite green after CSRF re-enable | automated | `cd backend && python -m pytest tests/ -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No Wave 0 required — all validation uses existing test infrastructure (77 tests in `backend/tests/`). No new test stubs needed per research findings.

---

## Manual Smoke Tests (post-execution)

These require a running dev environment and cannot be automated:

1. **CSRF round-trip:** Log in via Spotify → submit a like/dislike → verify 200 response (not 403)
2. **CSRF rejection:** `curl -X POST http://localhost:8000/api/submit-feedback/` without CSRF cookie → expect 403
3. **Frontend loads:** `npm run dev` in `frontend/` → visit `http://localhost:3000` → no console errors about missing env vars
4. **Spotify OAuth still works:** Visit `/spotify-login/` → complete OAuth flow → redirect to `/profile`
