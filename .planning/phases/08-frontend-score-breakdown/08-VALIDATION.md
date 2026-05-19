---
phase: 8
slug: frontend-score-breakdown
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-19
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — no frontend test framework configured |
| **Config file** | No `jest.config.*` or `vitest.config.*` found in `/frontend/` |
| **Quick run command** | `cd frontend && npx tsc --noEmit` |
| **Full suite command** | `cd frontend && npm run build` |
| **Estimated runtime** | ~15 seconds (tsc); ~60 seconds (build) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx tsc --noEmit`
- **After every plan wave:** Run `cd frontend && npm run build`
- **Before `/gsd-verify-work`:** Full build must be green (pre-existing `TopArtists.tsx` TS2345 error excluded from blame — baseline it first)
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | EXPLAIN-03 | — | Read-only render; no input surface | type-check | `cd frontend && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | EXPLAIN-03 | — | Empty state renders null, no crash | visual | Browser verification | N/A manual | ⬜ pending |
| 08-02-01 | 02 | 2 | METRIC-03 | — | Hit rate tile renders; null shows "—" | type-check + visual | `cd frontend && npx tsc --noEmit` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- No new test infrastructure required — phase is 4 file changes with no new business logic beyond a rounding formula.
- Existing infrastructure (`npx tsc --noEmit` + `npm run build`) covers automated verification.

*"Existing infrastructure covers all phase requirements." (manual browser verification is the stated gate for visual assertions)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Score bars render with correct labels and values | EXPLAIN-03 | No frontend test framework | Open browser, check DailyGem card displays 3 bars: Genre Match, Novelty, Feedback Influence with % values rounded to nearest 5% |
| Empty state for pre-migration gems | EXPLAIN-03 | No frontend test framework | Verify gem with no `score_breakdown` renders graceful empty state, no crash |
| Hit Rate tile in MetricsStrip | METRIC-03 | No frontend test framework | Check MetricsStrip shows Hit Rate tile alongside acceptance rate |
| `compound_hit_rate: null` shows "—" | METRIC-03 | No frontend test framework | Verify null value renders em-dash, not blank or error |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
