# Phase 10: v1.2 UX & Feedback Refinement - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** 10-v1-2-ux-feedback-refinement
**Areas discussed:** aiSyncedFeedback reset, EVOLVE-01 dispatch scope, Backend test strategy

---

## aiSyncedFeedback Reset Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — reset explicitly (Recommended) | Inside fetchGem, reset aiSyncedFeedback to null before the get() call. Mirrors how FeedbackButtonGroup resets selectedFeedback on trackId change (line 52). No stale state from previous gem. | ✓ |
| No — rely on FeedbackButtonGroup | FeedbackButtonGroup already resets selectedFeedback to null when trackId changes. The stale aiSyncedFeedback prop becomes a no-op because the new gem has a different trackId. | |

**User's choice:** Yes — reset explicitly
**Notes:** RESEARCH.md Open Question 1 resolved. Reset happens before get() call in fetchGem's try block.

---

## EVOLVE-01 Dispatch Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both — per EVOLVE-01 spec (Recommended) | Dispatch on every fetchGem call (initial load + force_new). ImprovementStory double-fetches on mount but both calls return identical data — idempotent, harmless. Simpler code path. | ✓ |
| force_new only | Pass a flag into fetchGem and only dispatch when force_new=true. Avoids the redundant fetch on initial mount. Slightly more complex logic. | |

**User's choice:** Both — per EVOLVE-01 spec
**Notes:** RESEARCH.md Open Question 2 resolved. Double-fetch on initial mount is acceptable. Follows spec exactly.

---

## Backend Test Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Wave 0 — before SYNC-01 implementation (Recommended) | Write test_build_prompt_contains_overall_sentiment and fallback extension first. Tests fail RED initially, then SYNC-01 makes them pass. Clean TDD. | ✓ |
| Alongside SYNC-01 | Write tests in the same task as the implementation. Less overhead, still gets coverage. | |

**User's choice:** Wave 0 — before SYNC-01 implementation
**Notes:** Both tests go in existing backend/tests/test_ai_feedback_service.py. No new test files.

---

## Claude's Discretion

- Exact placement of aiSyncedFeedback reset line within fetchGem (constraint: before get() call)
- Whether fetchMetrics in ImprovementStory uses useCallback or plain named function at component scope
- Code style and indentation within modified files (follow existing file conventions)

## Deferred Ideas

None — discussion stayed within phase scope.
