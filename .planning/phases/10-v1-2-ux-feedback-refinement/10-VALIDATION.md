---
phase: 10
slug: v1-2-ux-feedback-refinement
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-19
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

This phase has a **split verification contract** — there is no frontend test framework (RESEARCH.md confirmed: pytest backend only, no Jest/RTL). Backend changes are verified with pytest; frontend changes are verified with the TypeScript compiler (`npm run build`) plus source-assertion grep gates and manual visual checks.

| Property | Backend (SYNC-01) | Frontend (all UI / SYNC-02-03 / EVOLVE) |
|----------|-------------------|------------------------------------------|
| **Framework** | pytest | none (TypeScript compiler gate) |
| **Config file** | `backend/pytest.ini` | `frontend/tsconfig.json` (via `next build`) |
| **Quick run command** | `cd backend && python -m pytest tests/test_ai_feedback_service.py -x` | `cd frontend && npm run build` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x` | `cd frontend && npm run build` |
| **Estimated runtime** | ~5 seconds | ~30-60 seconds (Next.js build) |

`npm run build` is the frontend verification gate: it fails on TypeScript type errors and unused-variable errors, which catches the structural correctness of every UI/wiring edit. Behavioral/visual correctness is confirmed by the per-task grep assertions and the manual visual checks below.

---

## Sampling Rate

- **Backend tasks (SYNC-01, Plan 01):** after every task commit run `cd backend && python -m pytest tests/test_ai_feedback_service.py -x`
- **Frontend tasks (Plans 02 and 03):** after every task commit run `cd frontend && npm run build`
- **After every plan wave:** backend → `cd backend && python -m pytest tests/ -x`; frontend → `cd frontend && npm run build`
- **Before `/gsd:verify-work`:** backend full suite green AND frontend build green
- **Max feedback latency:** backend ~5s, frontend ~60s (Next.js build)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 10-01-01 | 01 | 1 | SYNC-01 | pytest (RED) | `cd backend && python -m pytest tests/test_ai_feedback_service.py -x -k "overall_sentiment"` | ⬜ pending |
| 10-01-02 | 01 | 1 | SYNC-01 | pytest (GREEN) | `cd backend && python -m pytest tests/test_ai_feedback_service.py -x` | ⬜ pending |
| 10-02-01 | 02 | 1 | UI-01 | build + grep | `cd frontend && npm run build` | ⬜ pending |
| 10-02-02 | 02 | 1 | UI-02, UI-03 | build + grep | `cd frontend && npm run build` | ⬜ pending |
| 10-02-03 | 02 | 1 | UI-04 | build + grep | `cd frontend && npm run build` | ⬜ pending |
| 10-03-01 | 03 | 2 | SYNC-02 | build + grep | `cd frontend && npm run build` | ⬜ pending |
| 10-03-02 | 03 | 2 | SYNC-03, EVOLVE-01 | build + grep | `cd frontend && npm run build` | ⬜ pending |
| 10-03-03 | 03 | 2 | EVOLVE-02 | build + grep | `cd frontend && npm run build` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Each frontend task's `<verify>` element promotes `cd frontend && npm run build` plus its source-assertion grep gates into `<automated>` blocks; `<human-check>` is retained for the visual/behavioral confirmation that the compiler cannot prove.

---

## Wave 0 Requirements

Wave 0 applies to the **backend only**. Plan 01 Task 1 is the Wave 0 step — it writes the two failing pytest tests before the implementation in Task 2.

- [ ] `backend/tests/test_ai_feedback_service.py` — add `test_build_prompt_contains_overall_sentiment` (asserts `"overall_sentiment"` in `_build_prompt` output)
- [ ] `backend/tests/test_ai_feedback_service.py` — add `test_fallback_interpretation_contains_overall_sentiment_key` (asserts `"overall_sentiment"` key present in fallback output)

**Frontend has no Wave 0** — no test framework is configured, so there are no test stubs to scaffold. Frontend tasks are gated by `npm run build` + grep assertions (already inside `<automated>` blocks) and do not reference any non-existent test files.

---

## Manual-Only Verifications

These behaviors cannot be proven by the compiler or grep and require visual/interaction confirmation in the browser.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TopArtists expanded panel background | UI-03 | `bg-gray-800` vs `bg-gray-850` renders differently; only visual inspection confirms a visible dark background | Open profile page, expand TopArtists section, confirm the expanded detail panel has a visible solid dark background (not transparent) |
| Popularity label tiers + colors | UI-02 | Color rendering and tier mapping confirmed visually | Confirm <40 → "Hidden Gem" (green), 40-69 → "Rising" (yellow), >=70 → "Mainstream" (gray); icon color matches text |
| Feedback toggle sync (no double API call) | SYNC-02, SYNC-03 | Network behavior + toggle state are runtime-only | Submit positive AI feedback → toggle flips to LIKE; negative → DISLIKE; neutral → unchanged; Network tab shows no second `/api/submit-feedback/` call |
| New-gem reset + live ImprovementStory refresh | EVOLVE-01, EVOLVE-02 | CustomEvent dispatch/refetch is runtime-only | Click "new gem" → toggle resets, ImprovementStory delta updates without page reload; no compounding duplicate requests (listener cleanup) |

---

## Validation Sign-Off

- [ ] All frontend tasks carry `cd frontend && npm run build` + grep assertions in `<automated>` blocks
- [ ] All backend tasks carry pytest commands in `<automated>` blocks (Wave 0 test stubs created in Plan 01 Task 1)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (every task now has an `<automated>` build or pytest gate)
- [ ] No Jest/RTL references; no non-existent test files referenced
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
</content>
