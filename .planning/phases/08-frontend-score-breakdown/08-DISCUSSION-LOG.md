# Phase 8: Frontend Score Breakdown - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-19
**Phase:** 08-frontend-score-breakdown
**Areas discussed:** Score bar placement, Score bar visual style, Empty state treatment, Hit rate tile label

---

## Score Bar Placement

| Option | Description | Selected |
|--------|-------------|----------|
| After explanation (Recommended) | Directly below the explanation blockquote — natural flow: explanation in words → numbers | ✓ |
| Separate section with header | Labeled "Why this gem?" block below feedback buttons | |
| After audio preview | Between audio preview and action buttons | |

**User's choice:** After explanation
**Notes:** User confirmed via wireframe review — layout matched expected positioning.

---

## Score Bar Visual Style

| Option | Description | Selected |
|--------|-------------|----------|
| Single color (Recommended) | All 3 bars use bg-green on bg-gray-800 — consistent with app accent | ✓ |
| Per-component colors | Genre = green, Novelty = blue-400, Feedback = orange | |
| Text-only | No bars — just three labeled percentage values inline | |

**User's choice:** Single color (bg-green)
**Notes:** Preferred minimal approach; zero new dependencies, consistent with existing Spotify-green palette throughout UI.

---

## Empty State Treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Hide bars entirely (Recommended) | If score_breakdown empty, render nothing where bars would be | ✓ |
| Greyed-out placeholder bars | Show all 3 bars at 0% with "Score data unavailable" caption | |

**User's choice:** Hide bars entirely
**Notes:** Pre-migration rows have score_breakdown={}. Clean hide is preferable to showing empty/dead state.

---

## Hit Rate Tile Label

| Option | Description | Selected |
|--------|-------------|----------|
| New tile alongside Acceptance Rate (Recommended) | Add Hit Rate next to Acceptance Rate — both visible | |
| Replace Acceptance Rate | Swap out acceptance rate for compound hit rate | ✓ |
| Rename with sub-label | "Hit Rate" + "liked + saved" sub-label below % | |

**User's choice:** Replace Acceptance Rate
**Notes:** Simpler strip; compound metric is more meaningful than liked-only signal. Label: "Hit rate" (lowercase, matches existing style).

---

## Claude's Discretion

- Exact Tailwind classes for bar height, corner radius, label/value typography
- Whether score bars are extracted as `ScoreBreakdown.tsx` or inlined in `DailyGem.tsx`
- Whether the bar container has a border/background or sits flush

## Deferred Ideas

None — discussion stayed within phase scope.
