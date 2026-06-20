# SongScope — Milestones

## v1.2 — UX & Feedback Refinement

**Shipped:** 2026-06-20
**Phases:** 10 (1 phase) | **Plans:** 3 | **Tasks:** ~12
**Git range:** `2640f5da` → `3487878c` (~2,426 insertions / 125 deletions)

Closed the visible feedback loop: AI text-feedback sentiment drives the like/dislike toggle (no double API call), taste-evolution stats live-refresh via a `songscope:new-gem` CustomEvent, and the profile UI was cleaned up (semantic popularity labels, visible expanded panel, no manual refresh button, clearer copy).

**Key accomplishments:**
1. `overall_sentiment` field added to the AI feedback JSON contract (prompt + fallback) via TDD — key always present, never `undefined` on the frontend (SYNC-01)
2. `FeedbackButtonGroup` mirrors AI sentiment into the thumbs toggle — visual only, no second API call (SYNC-02, SYNC-03)
3. `ImprovementStory` live-refreshes on every new gem via CustomEvent listener (EVOLVE-01, EVOLVE-02)
4. Semantic popularity labels (Hidden Gem / Rising / Mainstream) replace the inverted red/green scheme (UI-02)
5. Profile UI cleanup — removed stale Refresh button, fixed transparent expanded panel, clarified subtitles (UI-01, UI-03, UI-04)

**Known deferred items at close:** 5 (3 partial UAT phases + 2 human_needed verifications — see STATE.md Deferred Items). 1 carried tech-debt item: Phase 03 popularity-distribution update never implemented.

Archive: `milestones/v1.2-ROADMAP.md`, `milestones/v1.2-REQUIREMENTS.md`

---

## v1.1 — Explainability + Feedback Loop Closure

**Shipped:** 2026-05-19 (archived retroactively 2026-06-20)
**Phases:** 1–9 | **Plans:** 26

Took the recommendation engine from opaque to explainable and self-improving: fixed the broken foundation, built a real content-based scorer (taste vector + cosine similarity + novelty), closed the online feedback loop (taste-vector updates + Thompson-sampling bandit), hardened security, persisted score breakdowns, surfaced them in the UI, and documented the system for interviews.

**Key accomplishments:**
1. DB-backed known-song exclusion + repaired test suite + 5th candidate strategy (Phase 1)
2. Genre taste vector + cosine-similarity scorer + novelty formula (Phase 2)
3. Online taste-vector update + Thompson Sampling bandit over 5 sources (Phase 3)
4. Security hardening — secrets to env, CSRF re-enabled, exception-leak fixes (Phase 5)
5. Score breakdown persistence + compound hit metric + deterministic explanation (Phases 6–7)
6. 3-bar score breakdown UI + CONCEPTS/SYSTEM_DESIGN docs (Phases 8–9)

Archive: `milestones/v1.1-ROADMAP.md`, `milestones/v1.1-REQUIREMENTS.md`
