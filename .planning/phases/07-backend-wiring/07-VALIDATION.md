---
phase: 7
slug: backend-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` or `backend/setup.cfg` |
| **Quick run command** | `cd backend && python manage.py test apps.core.tests --keepdb` |
| **Full suite command** | `cd backend && python manage.py test --keepdb` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python manage.py test apps.core.tests --keepdb`
- **After every plan wave:** Run `cd backend && python manage.py test --keepdb`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 1 | EXPLAIN-01 | — | N/A | unit | `cd backend && python manage.py test tests.test_recommendation -k build_gem_explanation --keepdb` | ✅ | ⬜ pending |
| 7-01-02 | 01 | 1 | EXPLAIN-02, SCHEMA-02, SCHEMA-03 | — | N/A | unit | `cd backend && python manage.py test tests.test_recommendation -k score_breakdown --keepdb` | ✅ | ⬜ pending |
| 7-01-03 | 01 | 1 | SCHEMA-04 | — | N/A | unit | `cd backend && python manage.py test tests.test_recommendation -k cached_branch --keepdb` | ✅ | ⬜ pending |
| 7-02-01 | 02 | 2 | METRIC-02 | — | was_saved write failure must not 500 | unit | `cd backend && python manage.py test tests.test_views_gem_feedback -k was_saved --keepdb` | ✅ | ⬜ pending |
| 7-02-02 | 02 | 2 | METRIC-02 | — | N/A | unit | `cd backend && python manage.py test tests.test_views_gem_feedback -k compound_hit_rate --keepdb` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GET /api/daily-gem/ fresh day returns non-empty score_breakdown + explanation | SCHEMA-02, EXPLAIN-02 | Requires live Spotify OAuth session | Hit endpoint after clearing today's gem from DB; verify response JSON |
| GET /api/daily-gem/ cached branch returns same score_breakdown from DB | SCHEMA-04 | Requires two sequential calls same day | Call twice; assert score_breakdown identical and non-empty |
| Heart/save button sets was_saved=True | METRIC-02 | Requires live Spotify save action | Click save in UI; inspect DailyGem.was_saved in Django admin or shell |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
