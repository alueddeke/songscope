# Phase 10: v1.2 UX & Feedback Refinement - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Surgical wiring across 7 existing components to close the visible feedback loop:
1. AI text feedback → thumbs toggle sync (SYNC-01–03)
2. New gem generation → ImprovementStory live refresh (EVOLVE-01–02)
3. Profile page UI quality fixes: remove stale Refresh button, fix popularity labels, fix bg-gray-850 transparency, clarify section copy (UI-01–04)

No new components, no new API endpoints, no database migrations. All changes are edits to existing files. Phase ends when all 9 requirements pass.

</domain>

<decisions>
## Implementation Decisions

### aiSyncedFeedback Reset Behavior
- **D-01:** Reset `aiSyncedFeedback` to `null` explicitly inside `fetchGem` **before** the `get()` call — not after. This mirrors how `FeedbackButtonGroup` resets `selectedFeedback` on `trackId` change (line 52). Prevents stale sentiment from a previous gem syncing into the new gem's toggle on force_new.

### EVOLVE-01 Dispatch Scope
- **D-02:** Dispatch `window.dispatchEvent(new CustomEvent('songscope:new-gem'))` on **every** `fetchGem` call — both initial page load and `force_new`. The resulting double-fetch in `ImprovementStory` on initial mount is acceptable: the second call returns identical data (idempotent GET). Simplicity wins over micro-optimization.

### Backend Test Strategy
- **D-03:** Write the two SYNC-01 tests as **Wave 0** (before SYNC-01 implementation):
  - `test_build_prompt_contains_overall_sentiment` — asserts the string `"overall_sentiment"` appears in `_build_prompt` output
  - Extension to `test_interpret_feedback_fallback` — asserts `"overall_sentiment"` key is present in fallback output (even if `None`)
  - Tests must fail RED before SYNC-01 changes, then pass GREEN after.

### Claude's Discretion
- Exact placement of the `setAiSyncedFeedback(null)` reset line within `fetchGem` (before `get()` is the constraint; exact line within that scope is discretionary)
- Whether `fetchMetrics` in `ImprovementStory` is a `useCallback` or a plain named function at component scope (both work; plain named function is simpler given no dependency array needed)
- Exact indentation and code style within modified files (follow existing file conventions)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements (locked)
- `.planning/REQUIREMENTS.md` §v1.2 (SYNC-01 through UI-04) — exact requirement text for all 9 IDs; these are the acceptance conditions
- `.planning/ROADMAP.md` §Phase 10 — success criteria (5 must-be-TRUE statements)

### UI Design Contract (approved)
- `.planning/phases/10-v1-2-ux-feedback-refinement/10-UI-SPEC.md` — locked visual/interaction contract; component-by-component change table, interaction behavior specs (SYNC-02 null guard, EVOLVE-01/02 cleanup pattern, UI-01–04 exact copy/classes)

### Technical Research
- `.planning/phases/10-v1-2-ux-feedback-refinement/10-RESEARCH.md` — all architectural patterns, code examples, pitfalls, and open questions (resolved by D-01–D-03 above). MUST read before implementing SYNC or EVOLVE clusters.

### Components to Modify
- `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx` — SYNC-02
- `frontend/app/profile/components/DailyGem/DailyGem.tsx` — SYNC-03, EVOLVE-01
- `frontend/app/profile/components/Feedback/AIFeedbackInput.tsx` — read-only reference (already passes interpretation object to callback)
- `frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx` — EVOLVE-02
- `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` — UI-01
- `frontend/app/profile/components/TopArtists/TopArtists.tsx` — UI-02, UI-03
- `frontend/app/profile/page.tsx` — UI-04
- `backend/apps/ai/ai_feedback_service.py` — SYNC-01
- `backend/tests/test_ai_feedback_service.py` — Wave 0 + SYNC-01 tests

### Design System Reference
- `frontend/tailwind.config.ts` — confirms `green: "#1DB954"` custom alias, confirms no `gray-850` or `gray-750` in config (only standard Tailwind gray scale)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useEffect` with `[syncedFeedback]` dep — controlled prop pattern already used elsewhere in codebase; follow same guard structure (`if (syncedFeedback != null)`)
- `window.CustomEvent` — both DailyGem.tsx and ImprovementStory.tsx are `"use client"` (confirmed); no SSR hazard
- `text-green` Tailwind alias — project custom alias for #1DB954; safe to use in getPopularityLabel without config change
- `backend/tests/test_ai_feedback_service.py` — existing test file; Wave 0 tests extend it (don't create a new file)

### Established Patterns
- State declarations co-located above component body; add `aiSyncedFeedback` alongside existing state in DailyGem.tsx
- `useEffect` cleanup via `removeEventListener` — mandatory for EVOLVE-02 event listener to avoid memory leak on re-mount
- Conditional rendering: `{condition && <Component />}` — no changes needed for Phase 10 (all target sections already render unconditionally)
- `try/catch/finally` pattern in fetchGem — reset `aiSyncedFeedback` in the try block before `get()`, not in catch/finally

### Integration Points
- `AIFeedbackInput.tsx` line 88 already calls `onFeedbackSubmitted?.(response.interpretation)` — the CALLER already passes the object; only the RECEIVER in DailyGem.tsx needs updating
- `FeedbackButtonGroup` resets `selectedFeedback` on `trackId` change at line 52 — `aiSyncedFeedback` reset (D-01) is a parallel behavior in the parent component
- `_fallback_interpretation` in `ai_feedback_service.py` — must include `"overall_sentiment": None` key to ensure JSON serialization always produces the key (undefined ≠ null in JS)

</code_context>

<specifics>
## Specific Ideas

- RESEARCH.md Pitfall 1 (onFeedbackSubmitted signature mismatch) is the highest-risk pitfall — planner must ensure the inline `() => setShowFeedbackModal(true)` at DailyGem.tsx line 196 is replaced with a handler that both sets modal state AND reads `interpretation.overall_sentiment`
- RESEARCH.md Pitfall 4 (getPopularityLabel used in two places) — `getPopularityColor` called at BOTH line 158 (TrendingUp icon) and line 174 (text label); both must be replaced in one pass
- Wave 0 tests: 2 tests only, both in `backend/tests/test_ai_feedback_service.py`. Do not create new test files.
- RESEARCH.md Wave execution order: Wave 1 = SYNC-01 (backend only, after Wave 0 tests pass) + UI-01–04 (independent, low-risk); Wave 2 = SYNC-02/03 + EVOLVE-01/02 (state threading, verify together)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-v1-2-ux-feedback-refinement*
*Context gathered: 2026-06-19*
