# SongScope — Living Retrospective

## Milestone: v1.2 — UX & Feedback Refinement

**Shipped:** 2026-06-20
**Phases:** 1 (Phase 10) | **Plans:** 3

### What Was Built
- `overall_sentiment` added to the AI feedback JSON contract (prompt + fallback) via TDD RED-GREEN — key always present, never `undefined` on the frontend.
- `FeedbackButtonGroup` mirrors AI sentiment into the thumbs toggle (visual only, no second API call).
- `ImprovementStory` live-refreshes on every new gem via a `songscope:new-gem` CustomEvent listener.
- Profile UI cleanup: removed stale Refresh button, semantic popularity labels, fixed transparent expanded panel, clearer subtitles.

### What Worked
- Wave-based parallelism: 10-01 (backend contract) and 10-02 (UI fixes) ran in parallel with no file overlap; 10-03 consumed the 10-01 contract in Wave 2.
- TDD on the contract field (10-01) guaranteed the frontend equality check never sees `undefined` — the bug was designed out, not patched.
- CustomEvent decoupling avoided prop-drilling between gem generation and stats refresh.

### What Was Inefficient
- Version labeling drift: Phase 10 was committed as `feat(v1.2)` while GSD config still tracked `v1.1`, and v1.1 was never formally archived. Milestone close had to reconcile three sources (config, commits, PROJECT.md) and retroactively archive v1.1.
- The original v1.2 goal (full-cascade feedback filtering) was much larger than what shipped; scope narrowed to the sentiment-sync/UI slice mid-milestone without updating PROJECT.md's stated goal until close.

### Patterns Established
- CustomEvent for cross-component live refresh without shared state.
- Contract fields defended by "always present" guarantees (prompt + fallback both emit the key).
- Semantic, domain-appropriate labels over raw numeric color scales.

### Key Lessons
- Keep GSD milestone metadata in lockstep with commit version tags — divergence creates archive ambiguity at close.
- When a milestone goal narrows, update PROJECT.md immediately so the close audit isn't surprised.
- Carry verification/UAT debt explicitly: phases 03/05/08 shipped with browser-only UAT pending; recording them as Deferred Items keeps them visible.

### Cost Observations
- Single-day milestone (2026-06-19), 3 plans, ~2,426 insertions.
- Model mix: opus (planning) / sonnet (execution) per config.

---

## Milestone: v1.1 — Explainability + Feedback Loop Closure

**Shipped:** 2026-05-19 (documented retroactively at v1.2 close)
**Phases:** 9 | **Plans:** 26

### What Was Built
Foundation fixes (known-song exclusion, crash fixes, test suite repair) → content-based scorer (taste vector + cosine similarity + novelty) → online feedback loop (taste-vector updates + Thompson-sampling bandit) → security hardening → score-breakdown persistence + compound metric + deterministic explanation → 3-bar UI + docs.

### Key Lessons
- The cached-branch trap (3 return sites in `get_daily_gem`) was flagged in planning and all three were fixed — pre-identifying the trap prevented a silent `{}` regression.
- Deterministic explanation template (no OpenAI) gave zero-cost, zero-latency, formula-synchronized output — the right call for a budget-constrained portfolio app.
- Phase 03's popularity-distribution update was a ROADMAP deliverable never specified as a plan must-have, so it was never built — a reminder that ROADMAP deliverables must be lowered into plan must-haves or they fall through.

---

## Cross-Milestone Trends

| Trend | Observation |
|-------|-------------|
| Verification debt | Browser-only UAT (phases 03, 05, 08) consistently deferred — single-user app with no automated E2E harness |
| Scope discipline | Larger milestone goals (full-cascade filtering) tend to narrow to shippable slices; capture the narrowing in PROJECT.md sooner |
| Contract safety | TDD + "always-present key" guarantees prevented frontend `undefined` bugs — worth repeating |
| ROADMAP → plan gap | Deliverables not lowered into plan must-haves get dropped (Phase 03 popularity range) |
