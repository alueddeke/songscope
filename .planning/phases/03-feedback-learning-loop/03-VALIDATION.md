---
phase: 3
slug: feedback-learning-loop
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `backend/pytest.ini` or `backend/setup.cfg` |
| **Quick run command** | `cd backend && python -m pytest apps/recommendations/tests/ apps/core/tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest apps/recommendations/tests/ apps/core/tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | D-01..D-05 | — | N/A | unit | `cd backend && python -m pytest apps/recommendations/tests/test_personalization_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | D-01,D-02,D-03 | — | N/A | unit | `cd backend && python -m pytest apps/recommendations/tests/test_personalization_engine.py::test_apply_feedback_like -x -q` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | D-04 | — | N/A | unit | `cd backend && python -m pytest apps/recommendations/tests/test_personalization_engine.py::test_remove_feedback_unlike -x -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 0 | D-06..D-09 | — | N/A | unit | `cd backend && python -m pytest apps/recommendations/tests/test_bandit.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | D-07,D-08 | — | N/A | unit | `cd backend && python -m pytest apps/recommendations/tests/test_bandit.py::test_thompson_sampling_weights -x -q` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 0 | D-10..D-12 | — | N/A | unit | `cd backend && python -m pytest apps/recommendations/tests/test_popularity_targeting.py -x -q` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 3 | D-13,D-14 | — | N/A | integration | `cd backend && python -m pytest apps/core/tests/test_daily_gem_view.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/apps/recommendations/tests/test_personalization_engine.py` — stubs for D-01..D-05
- [ ] `backend/apps/recommendations/tests/test_bandit.py` — stubs for D-06..D-09
- [ ] `backend/apps/recommendations/tests/test_popularity_targeting.py` — stubs for D-10..D-12
- [ ] `backend/apps/core/tests/test_daily_gem_view.py` — stubs for D-13, D-14
- [ ] `pip install openai` — required for RecommendationExplainer (not currently installed)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OpenAI-generated gem explanation includes score breakdown language | D-13 | Requires live OpenAI API key | Like a track, call /api/daily-gem/, read explanation field for genre/novelty/feedback references |
| Bandit weights converge toward better-performing sources over 10+ feedback events | D-08 | Statistical — needs real usage cycle | Submit 5+ likes on playlist_mining tracks, verify source_stats['playlist_mining']['s'] increments and get_recommendation_weights() returns higher weight for that source |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
