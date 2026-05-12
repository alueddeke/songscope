---
phase: 4
slug: metrics-evaluation-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-12
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds (62 existing tests) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | Wave 0 | — | N/A | setup | `cd backend && python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | D-01/D-02 | — | metrics only from owned user data | unit | `pytest tests/test_metrics.py -x -q` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | D-03 | — | trend only from owned user data | unit | `pytest tests/test_metrics.py::TestTrendEndpoint -x -q` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 1 | D-10/D-11 | — | Jaccard zero when genres empty | unit | `pytest tests/test_metrics.py::TestJaccard -x -q` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | D-05/D-06 | — | chart renders without crash | manual | n/a | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 3 | D-12/D-13 | — | docs at repo root | smoke | `ls CONCEPTS.md SYSTEM_DESIGN.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_metrics.py` — unit tests for `get_recommendation_metrics`, `get_recommendation_trend`, Jaccard helper, and `top_genres` normalization
- [ ] `npm install recharts` in `frontend/` — required before any chart component can be built

*Existing pytest-django infrastructure covers all other framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Like-rate trend chart renders with correct x/y axes | D-08 | Visual chart output | Load `/profile`, scroll to bottom, verify line chart shows date x-axis and 0–100% y-axis |
| Taste profile bar chart shows top 10 genres | D-07 | Visual chart output | Same page, verify horizontal bar chart with genre names on y-axis |
| Recharts colors match `#1DB954` green | D-05 | Visual color check | Inspect chart lines/bars, confirm green matches MetricsStrip accent |
| CONCEPTS.md covers Thompson Sampling with formula | D-14 | Content quality | Open `CONCEPTS.md`, verify §Thompson Sampling has formula + code snippet |
| SYSTEM_DESIGN.md Mermaid diagram renders on GitHub | D-13 | Platform rendering | View on GitHub, verify diagram renders (not raw text) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
