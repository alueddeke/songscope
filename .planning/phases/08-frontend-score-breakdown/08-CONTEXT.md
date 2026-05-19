# Phase 8: Frontend Score Breakdown - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Render score breakdown data and compound hit rate in the UI. Two surfaces:

1. **Score bars on gem card**: Three labeled progress bars (Genre Match, Novelty, Feedback) rendered from `score_breakdown` API data, placed directly below the explanation blockquote in `DailyGem.tsx`
2. **MetricsStrip hit rate**: Replace the "Acceptance rate" `<Stat>` tile with "Hit rate" sourced from `compound_hit_rate`

Phase ends when both UI requirements (EXPLAIN-03, METRIC-03) are satisfied. No new backend work — all data fields are live from Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Score Bar Placement

- **D-01:** Score bars appear **directly below the explanation blockquote** — natural reading flow (why in words → why in numbers). Placed before the audio preview section.
- **D-02:** If `score_breakdown` is empty or missing (pre-migration rows), **hide bars entirely** — no placeholder, no message, no greyed-out state. The explanation text still renders if present.

### Score Bar Visual Style

- **D-03:** All 3 bars use **single color** — `bg-green` fill on `bg-gray-800` track. No per-component color differentiation. Consistent with Spotify green accent used throughout the app.
- **D-04:** Layout: label left, percentage right, bar full-width between. Each row: `[Label] [bar] [XX%]`.
- **D-05:** Percentages **rounded to the nearest 5%** (per ROADMAP.md success criterion). Formula: `Math.round(value * 100 / 5) * 5`.
- **D-06:** Bar labels: "Genre Match", "Novelty", "Feedback" (short, fits single line).

### Compound Hit Rate (MetricsStrip)

- **D-07:** **Replace** "Acceptance rate" `<Stat>` tile with "Hit rate". The `gem_acceptance_rate` stat is removed from the displayed strip; `compound_hit_rate` takes its slot.
- **D-08:** Display label: **"Hit rate"** (lowercase, matches existing label style: "Gems shown", "Hidden gem rate").
- **D-09:** Value format: `${Math.round(compound_hit_rate * 100)}%` — same pattern as existing acceptance rate rendering.

### TypeScript Interface Updates

- **D-10:** `DailyGemResponse` interface in `DailyGem.tsx` needs `score_breakdown: Record<string, number>` added (optional or defaulting to `{}`).
- **D-11:** `Metrics` interface in `MetricsStrip.tsx` needs `compound_hit_rate: number | null` added; `gem_acceptance_rate` can remain for type safety but won't be displayed.

### Claude's Discretion

- Exact Tailwind classes for bar height, corner radius, and label/value typography (consistent with surrounding text scale)
- Whether score bars are extracted into a `ScoreBreakdown.tsx` sub-component or inlined in `DailyGem.tsx` (follow existing pattern — `FeedbackButtonGroup` is a separate file; if bars are >20 lines, extract)
- Whether the bar container has a border/background or sits flush (match existing blockquote and section visual weight)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §EXPLAIN-03, §METRIC-03 — exact success criteria and acceptance conditions (locked)
- `.planning/ROADMAP.md` §Phase 8 — 3 success criteria that must be TRUE (bars render, graceful empty state, MetricsStrip hit rate tile)

### Components to Modify
- `frontend/app/profile/components/DailyGem/DailyGem.tsx` — primary target; add score bars below explanation blockquote; update `DailyGemResponse` interface to include `score_breakdown`
- `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` — replace `gem_acceptance_rate` stat with `compound_hit_rate`; update `Metrics` interface

### Data Contracts (from Phase 7)
- `backend/apps/core/views.py` `get_daily_gem` — returns `score_breakdown: dict` in response; keys: `genre_sim`, `novelty`, `feedback_multiplier` (0–1 floats)
- `backend/apps/core/views.py` `get_recommendation_metrics` — returns `compound_hit_rate: float` (0.0 when no gems)

### Prior Phase Context
- `.planning/phases/07-backend-wiring/07-CONTEXT.md` — D-12, D-13: `compound_hit_rate` key always present in metrics response even when 0; `score_breakdown` always populated for new gems

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `<Stat label value>` component in `MetricsStrip.tsx` — drop-in for the new "Hit rate" tile; no changes to the Stat component needed
- Tailwind custom color `green` (`#1DB954`) — use `bg-green` for bar fill (already in `tailwind.config.ts`)
- `bg-gray-800` — use as bar track background (used throughout for subtle containers)
- `popularityLabel` helper in `DailyGem.tsx` — pattern for a pure display helper; `ScoreBreakdown` sub-component (if extracted) follows same style

### Established Patterns
- `"use client"` directive required — both target components already have it
- Props interfaces co-located above component function — add `score_breakdown` to `DailyGemResponse` inline
- Conditional rendering: `{explanation && (<blockquote>...)}` — same pattern for `{hasScores && (<ScoreBars />)}`
- `try/catch/finally` data fetching — no changes needed; bars render from existing `gem` state

### Integration Points
- `DailyGem.tsx`: `gem.score_breakdown` available once `DailyGemResponse` interface is updated; no new API calls
- `MetricsStrip.tsx`: `metrics.compound_hit_rate` available once `Metrics` interface is updated; no new API calls
- Both fields come from existing GET calls that Phase 7 wired up — pure frontend rendering work

</code_context>

<specifics>
## Specific Ideas

- Wireframe confirmed by user:
  ```
  Genre Match   [███████░░░]  75%
  Novelty       [██████░░░░]  60%
  Feedback      [██░░░░░░░░]  20%
  ```
  Placed between explanation blockquote and audio preview. Single green color, full-width bars with label+% flanking.

- MetricsStrip confirmed layout:
  ```
  Gems shown  Gems liked  Hit rate  Avg popularity  Hidden gem rate
      12           5        58%        31/100            73%
  ```
  "Acceptance rate" slot replaced by "Hit rate".

- Empty state confirmed: bars simply don't render when `score_breakdown` is `{}` or missing — no placeholder needed.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-frontend-score-breakdown*
*Context gathered: 2026-05-19*
