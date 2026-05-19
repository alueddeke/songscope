---
phase: 08-frontend-score-breakdown
plan: "01"
subsystem: frontend
tags: [frontend, react, nextjs, tailwind, score-breakdown, metrics-strip]
dependency_graph:
  requires:
    - "07-backend-wiring/07-01 — backend writes score_breakdown to DailyGem model and returns it in /api/daily-gem/"
    - "07-backend-wiring/07-02 — backend computes compound_hit_rate and returns it in /api/recommendation-metrics/"
  provides:
    - "ScoreBreakdown.tsx — 3-bar labeled progress display rendered from gem.score_breakdown"
    - "MetricsStrip.tsx — Hit rate tile sourced from metrics.compound_hit_rate replacing Acceptance rate"
  affects:
    - "frontend/app/profile/components/DailyGem/DailyGem.tsx — interface + import + JSX"
    - "frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx — interface + stat swap"
tech_stack:
  added: []
  patterns:
    - "Sub-component extraction at the ~20-line threshold — mirrors FeedbackButtonGroup.tsx pattern"
    - "Fixed-order display constant (SCORE_ROWS) for dict-shaped API data — avoids Object.keys iteration order bugs"
    - "Defensive != null (loose) for new optional fields on pre-existing endpoint shapes — guards undefined on old cached responses"
key_files:
  created:
    - frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx
  modified:
    - frontend/app/profile/components/DailyGem/DailyGem.tsx
    - frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx
decisions:
  - "D-01: Score bars placed directly below explanation blockquote, before audio preview"
  - "D-02: Empty score_breakdown returns null from ScoreBreakdown — no placeholder"
  - "D-03: Single accent color bg-green fill on bg-gray-800 track for all bars"
  - "D-04: [Label][bar][XX%] row layout via flex with fixed-width label/percentage and flex-1 track"
  - "D-05: Nearest-5% rounding formula Math.round(raw * 100 / 5) * 5"
  - "D-06: Labels locked as Genre Match / Novelty / Feedback (from SCORE_ROWS constant)"
  - "D-07: Acceptance rate stat replaced by Hit rate in MetricsStrip"
  - "D-08: Label is exactly Hit rate (sentence case)"
  - "D-09: Value formatted as Math.round(compound_hit_rate * 100)% — integer, no decimals"
  - "D-10: DailyGemResponse interface has score_breakdown: Record<string, number> (required, not optional)"
  - "D-11: gem_acceptance_rate kept in Metrics interface for type safety; compound_hit_rate added"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-05-19"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 2
requirements_completed: [EXPLAIN-03, METRIC-03]
---

# Phase 8 Plan 01: Frontend Score Breakdown Summary

**One-liner:** 3-bar score breakdown on gem cards + Hit rate stat in MetricsStrip wired to Phase 7 API fields (`score_breakdown`, `compound_hit_rate`).

## What Was Built

### Task 1 — ScoreBreakdown.tsx (new file)

Created `frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx` as a standalone client component following the `FeedbackButtonGroup` sub-component extraction pattern. Key implementation details:

- `SCORE_ROWS` constant (module-level, before the function) maps the 3 API keys to display labels in locked order: `genre_sim` → "Genre Match", `novelty` → "Novelty", `feedback_multiplier` → "Feedback"
- Empty-state guard at top of function body: `if (Object.keys(breakdown).length === 0) return null` — prevents any DOM emission for pre-Phase-7 legacy rows
- Per-row layout: flex row with `w-28 flex-shrink-0` label span, `flex-1 bg-gray-800 rounded-full h-2 overflow-hidden` track div, inline `style={{ width: \`${pct}%\` }}` fill div with `bg-green`, and `w-9 text-right flex-shrink-0` percentage span
- Rounding formula: `Math.round(raw * 100 / 5) * 5` — nearest 5%
- `breakdown[key] ?? 0` guards against backend omitting a key

### Task 2 — DailyGem.tsx (4 additive edits)

- Added `score_breakdown: Record<string, number>` to `DailyGemResponse` interface (required, not optional — API guarantees presence per Phase 7)
- Imported `ScoreBreakdown` from `./ScoreBreakdown` after the `FeedbackButtonGroup` import line
- Extended destructure `const { track, explanation, date, score_breakdown } = gem` — placed after the existing null guard at line 75 (Pitfall 1 avoided)
- Inserted `{/* Score breakdown */}` comment + `<ScoreBreakdown breakdown={score_breakdown ?? {}} />` JSX between the explanation blockquote and the audio preview block

### Task 3 — MetricsStrip.tsx (3 edits)

- Added `compound_hit_rate: number | null` to `Metrics` interface immediately after `gem_acceptance_rate` (kept for type safety per D-11)
- Replaced `acceptance` derivation with `hitRate` using `metrics.compound_hit_rate != null` (loose not-equal — guards both `null` and `undefined` per Pitfall 2) and formats as `${Math.round(metrics.compound_hit_rate * 100)}%`
- Swapped `<Stat label="Acceptance rate" value={acceptance} />` with `<Stat label="Hit rate" value={hitRate} />`

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 | e29ad51a | feat(08-01): create ScoreBreakdown.tsx sub-component |
| 2 | 7b4b7f51 | feat(08-01): wire ScoreBreakdown into DailyGem.tsx |
| 3 | 2e89e1d4 | feat(08-01): replace Acceptance rate stat with Hit rate in MetricsStrip.tsx |

## Verification

- `npx tsc --noEmit` returns exactly 1 error (pre-existing `TopArtists.tsx:85` TS2345 baseline — unrelated to this phase)
- All acceptance criteria grep/awk checks passed for all 3 tasks
- No stubs, no placeholders, no TODO comments

## Deviations from Plan

None — plan executed exactly as written. All 11 decisions (D-01 through D-11) honored. All acceptance criteria passed on first attempt.

## Known Stubs

None — all three files have complete implementations. `ScoreBreakdown` renders real data from the API. `MetricsStrip` displays real `compound_hit_rate` from the API. No hardcoded values flow to the UI.

## Milestone v1.1 Readiness

Phase 8 closes EXPLAIN-03 (score breakdown bars in gem card) and METRIC-03 (Hit rate stat in MetricsStrip). Combined with Phase 7 (backend wiring), the complete explainability surface is live. Only Phase 9 (documentation sync — DOCS-01, DOCS-02) remains for v1.1 milestone completion.

## Self-Check: PASSED

- `frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx` — FOUND
- `frontend/app/profile/components/DailyGem/DailyGem.tsx` — FOUND (modified)
- `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` — FOUND (modified)
- Commit e29ad51a — FOUND
- Commit 7b4b7f51 — FOUND
- Commit 2e89e1d4 — FOUND
- TypeScript error count: 1 (pre-existing baseline only)
