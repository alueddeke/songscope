# Research Summary — SongScope v1.1

**Project:** SongScope
**Milestone:** v1.1 — Explainability + Feedback Loop Closure
**Researched:** 2026-05-13
**Confidence:** HIGH — all findings grounded in direct codebase inspection + Spotify API changelog verification

---

## Executive Summary

SongScope v1.1 is a brownfield milestone on a working Django REST + Next.js music recommendation app. The goal is to surface why each daily gem was chosen (score breakdown UI) and to close the feedback loop with a measurable compound success metric (hit = liked OR saved). Research across all four areas converges on one key finding: **the infrastructure for both features already exists in the codebase — the work is wiring, not building.** The `score_breakdown` dict is computed on every recommendation, the `explanation` TextField is on the model, the `current_user_saved_tracks_contains` spotipy method is installed, Recharts and Tailwind are available, and the `user-library-read` OAuth scope is already in the scope string. Zero new dependencies are required.

The recommended implementation strategy is strictly additive: one Django migration adds `score_breakdown` (JSONField), `was_saved` (BooleanField null=True), and `score_total` (FloatField null=True) to `DailyGem`; a deterministic Python template function generates explanation text at gem creation time (no OpenAI call); and a new `ScoreBreakdown` React component renders the three score dimensions from the API response. The compound success metric is defined as `was_liked OR was_saved` — not AND — because requiring both in a single-user daily-gem app produces too sparse a label. The "played" component was explicitly dropped after confirming that Spotify's playback state API requires Premium and has 403 restrictions for Dev Mode apps post-February 2026.

The primary execution risk is the **cached-gem branch trap**: `get_daily_gem` has three return sites (line 1048, line 1110, line 1126) and the cached branch currently hardcodes `score_breakdown: {}`. Any implementation that only updates the fresh branch will ship a feature that works on day 1 and silently breaks on every subsequent load. The second major trap is the **two-path compound metric problem**: `submit_feedback` and `add_track_to_liked` are independent code paths — `was_saved` must be written in `add_track_to_liked`, not in `submit_feedback`. Build order is non-negotiable: migration first, then backend, then frontend.

---

## Key Findings

### Stack

No new dependencies are required for any feature in this milestone. Every library, scope, and endpoint needed is already installed or already granted:

- **Django JSONField (built-in):** `score_breakdown` and `was_saved` are straightforward nullable column additions. SQLite supports JSONField since Django 3.1; project runs Django 5.1.3.
- **spotipy 2.25.1 (installed):** `current_user_saved_tracks_contains([track_id])` provides the "was saved" half of the compound metric. The `user-library-read` scope is already in the OAuth scope string.
- **Spotify API deprecations (confirmed):** `GET /v1/audio-features` and `GET /v1/recommendations` removed November 2024. `GET /v1/me/player/currently-playing` requires Spotify Premium + Extended Quota Mode as of February 2026 — unreliable for this project. Playback-based compound metric is off the table.
- **Recharts ^3.8.1 + Tailwind ^3.4.1 (installed):** Score breakdown UI needs no new frontend dependencies. Tailwind div-bars (percentage-width divs) are recommended over Recharts for three static bars — lighter and already the pattern in the codebase.
- **openai 1.99.9 (installed):** Available for richer explanation text, but the deterministic template approach is preferred: zero cost, zero latency, fully testable, and keeps the explanation synchronized with the formula by construction.

One housekeeping item: `requirements.txt` pins `spotipy==2.23.0` but the venv has `2.25.1` installed. Update the pin.

### Features

**Must have (table stakes):**
- **Score component display** — any ML app claiming explainability must show what factors drove the pick; the data is already returned on the fresh branch, just not persisted or rendered
- **Human-readable explanation text** — deterministic template tied to the dominant score component (genre match / novelty / feedback bonus); must not be canned copy disconnected from the actual score
- **Score persisted at recommendation time** — without persistence, offline evaluation is impossible; the `(score_components, outcome)` training pair in a single table is the foundation for the future evaluation dashboard milestone
- **Binary outcome label (`was_saved`)** — the compound metric requires a ground truth label; `was_liked` exists; `was_saved` is the missing half
- **Compound hit rate in metrics strip** — `(was_liked OR was_saved) / total_gems` as a visible metric; this is the headline deliverable that proves the feedback loop is closed

**Should have (differentiators):**
- **Score component bar chart** — text + visual hybrid builds more user trust than either alone per ACM RecSys 2024 research; three proportional bars in Tailwind, no Recharts needed for static display
- **Source attribution in explanation** — "Found via your playlists" adds transparency to the Thompson Sampling bandit strategy; `source` is already in `score_breakdown`
- **Dynamic explanation logic** — explanation adapts to the dominant component rather than a fixed string; low complexity, high interview value

**Defer to future milestones:**
- `taste_vector_snapshot` at creation time — useful for longitudinal analysis but not blocking
- `preview_clicked` event logging — Spotify deprecated `preview_url` on many tracks; signal quality unclear
- Confidence intervals / model uncertainty display — requires hundreds of data points
- A/B explanation format testing — no multi-user base to test against

**Anti-features to avoid:**
- Decimal-precision percentages in the UI (e.g., "73.4%") — round to nearest 5% or use Low/Medium/High labels; decimals read as algorithmic output, not human reasoning
- OpenAI call for explanation generation — adds latency and cost to an already multi-step endpoint; deterministic template is the correct solution
- Real-time playback detection — Spotify API restrictions make this unreliable; document the decision for interview contexts

### Architecture

The architecture is additive throughout. The engine already writes `score_breakdown` to every candidate dict; the only missing link is writing it to the DB and reading it back on cached responses. The compound metric annotates the existing `add_track_to_liked` endpoint with a silent DB update. The explanation is generated by a pure Python helper function called at gem creation time.

**Major components touched:**
1. **`DailyGem` model** — adds `score_breakdown` JSONField (default=dict), `score_total` FloatField null=True, and `was_saved` BooleanField null=True; one migration
2. **`get_daily_gem` view** — fresh branch writes score fields + calls `_build_gem_explanation()`; cached branch reads score fields from DB and constructs `explanation_data` dict; all three return sites must be updated
3. **`add_track_to_liked` view** — after successful Spotify save, calls `DailyGem.objects.filter(user, track).update(was_saved=True)`; wrapped in try/except so a DB failure does not 500 the save action
4. **`get_recommendation_metrics` view** — adds `compound_hit_rate = (was_liked OR was_saved) / total` to response
5. **`ScoreBreakdown` React component** — renders genre%, novelty%, feedback label, and source tag from `explanation_data`; new component in `frontend/app/profile/components/`

**Data flow:**
```
Engine._score_recommendations() → rec['score_breakdown']
  ↓ (fresh branch only, currently)
get_daily_gem → persist to DailyGem.score_breakdown + generate explanation text
  ↓ (both branches, after fix)
API response: { explanation, explanation_data, score_breakdown }
  ↓
ScoreBreakdown component renders three bars + source tag

add_track_to_liked → sp.current_user_saved_tracks_add()
  → DailyGem.filter(user, track).update(was_saved=True)  [silent, non-fatal]

Metrics view → compound_hit_rate = Q(was_liked=True) | Q(was_saved=True)
```

**Schema design decision:** Use `score_breakdown = JSONField(default=dict)` for the primary stored representation (one migration, open schema, directly mirrors engine output), plus `score_total = FloatField(null=True)` as a flat column for the one aggregate metric that matters (`Avg('score_total')`). This satisfies both the "single migration" constraint and the "queryable total score" need without the full four-column approach from ARCHITECTURE.md.

### Critical Pitfalls

1. **Cached-branch returns `{}` — three return sites, all must be fixed** (PITFALLS Pitfall 1). The `get_daily_gem` view has return statements at lines 1048, 1110, and 1126. Score breakdown must be read from DB on all three cached-branch paths. Test by calling the endpoint twice on the same day and asserting `score_breakdown` is non-empty on both responses.

2. **`add_track_to_liked` and `submit_feedback` are separate code paths** (PITFALLS Pitfall 4). `DailyGem.was_liked` is written in `submit_feedback`; `DailyGem.was_saved` must be written in `add_track_to_liked`. Neither calls the other. If `was_saved` is wired to `submit_feedback`, it will never fire from the heart-button click. The compound metric is silently dark.

3. **Formula-explanation drift** (PITFALLS Pitfall 3). The Thompson Sampling source multiplier is applied *after* the `score_breakdown` dict is populated — the stored breakdown is the pre-bandit formula score, not the final ranking score. Accept this and document: "explanation reflects the scoring formula components; source discovery weight is applied separately and noted in the source tag."

4. **NULL history after migration** (PITFALLS Pitfall 2). All existing `DailyGem` rows get `score_breakdown = {}` and `was_saved = NULL`. Never `coalesce(score_component, 0)` in metrics queries — that false-fills pre-migration rows as score-zero failures. Filter on `score_breakdown != {}` or document the migration epoch boundary in query comments.

5. **OpenAI over-engineering trap** (PITFALLS Pitfall 5). Adding a synchronous OpenAI call to `get_daily_gem` adds latency to an already multi-step endpoint, consumes the $1/day budget, and creates prompt-formula drift. Use a deterministic `_build_gem_explanation(breakdown, track_name, artist_name) -> str` helper. No OpenAI, no template engine, one pure function with unit tests.

---

## Implications for Roadmap

The build order is a hard dependency chain: schema must exist before the view can write to it; the view must return the fields before the frontend can render them.

### Phase 1: Schema Migration

**Rationale:** Everything downstream depends on the DB columns existing. Zero-risk, zero-user-impact — all new columns are nullable with defaults. Apply and verify before writing any view code.

**Delivers:** `DailyGem` model extended with `score_breakdown` (JSONField default=dict), `score_total` (FloatField null=True), `was_saved` (BooleanField null=True), and optionally `source_at_recommendation` (CharField max_length=50 blank=True). Migration `0008_dailygem_explainability.py` applied.

**Addresses:** Score persistence (FEATURES table stakes), compound metric label (FEATURES table stakes)

**Avoids:** PITFALL 7 (JSON vs float column indecision — resolved upfront)

**Research flag:** No — standard Django AddField migration.

---

### Phase 2: Backend — Score Persistence + Explanation Generation

**Rationale:** Must come before frontend. Two discrete changes: (a) persist score fields at gem creation on the fresh branch and generate explanation text, (b) fix all three cached-branch return sites to read from DB. Extend `add_track_to_liked` with the silent `was_saved` annotation. Add compound hit rate to metrics view.

**Delivers:**
- Fresh branch writes `score_breakdown`, `score_total`, and `explanation` to `DailyGem` at creation
- All three cached-branch return sites return `explanation_data` and populated `score_breakdown` from DB
- `add_track_to_liked` writes `DailyGem.was_saved = True` on successful Spotify save (non-fatal try/except)
- `get_recommendation_metrics` returns `compound_hit_rate`

**Addresses:** Score persistence, explanation text (FEATURES table stakes), compound metric wiring (FEATURES table stakes)

**Avoids:** PITFALL 1 (cached-branch `{}`), PITFALL 2 (NULL epoch boundary documented in code), PITFALL 4 (two-path compound metric — `was_saved` in `add_track_to_liked`, not `submit_feedback`), PITFALL 5 (no OpenAI in explanation path)

**Key implementation notes:**
- Explanation template logic: genre_sim dominant (>0.5) → "Matches your taste in [top_genre]"; novelty dominant or popularity < 35 → "A hidden gem — popularity [n], outside the mainstream"; feedback_multiplier == 1.5 → "From an artist you've liked before"; fallback → "Picked for your listening patterns". Append "Found via [source_human_readable]".
- `add_track_to_liked` change: `DailyGem.objects.filter(user=request.user, track=track_obj).update(was_saved=True)` — use `filter().update()` not `get()` to handle track appearing on multiple dates
- `compound_hit_rate` query: `DailyGem.objects.filter(Q(was_liked=True) | Q(was_saved=True)).count() / total`

**Research flag:** No — all code paths confirmed in codebase; pattern is standard Django view extension.

---

### Phase 3: Frontend — Score Breakdown UI

**Rationale:** Depends on Phase 2 API returning `explanation_data`. Can be developed against a local mock, but integration requires Phase 2 backend changes.

**Delivers:**
- `explanation_data` and `score_breakdown` added to `DailyGemResponse` TypeScript interface
- New `ScoreBreakdown` component rendering genre_sim_pct (bar), novelty_pct (bar), feedback_mult_label (badge), source_label (tag)
- Component mounted in `DailyGem.tsx` below existing `<blockquote>` explanation block
- Graceful empty state when `explanation_data` is absent (old/unscored gems)

**Addresses:** Score component display, source attribution (FEATURES table stakes + differentiators)

**Avoids:** PITFALL 8 (API contract drift — TypeScript interface defined; optional chaining on all field reads)

**Key implementation notes:**
- Use Tailwind percentage-width divs for bars, not Recharts — three static bars do not justify the overhead
- Round all percentages to nearest 5% for display: `Math.round(pct / 5) * 5`
- `feedback_mult_label` options: "liked artist" (mult > 1.2), "skipped artist" (mult < 0.8), "neutral"
- Source label mapping: `playlist_mining → "your playlists"`, `artist_network → "artist connections"`, `related_artists → "similar artists"`, `genre_search → "genre exploration"`, `contextual → "listening patterns"`
- `AddToLiked` component requires no changes — backend silently annotates `was_saved`

**Research flag:** No — Tailwind bar pattern is established in codebase.

---

### Phase 4: Metrics Visibility + Docs

**Rationale:** Can run in parallel with Phase 3 or immediately after. Ties compound hit rate into the existing metrics strip and satisfies the project memory requirement to update CONCEPTS.md + SYSTEM_DESIGN.md with every code change.

**Delivers:**
- `MetricsStrip` updated to show "Hit Rate" (compound_hit_rate from API)
- CONCEPTS.md updated: compound hit rate definition, why save > play for signal quality, formula-explanation drift design decision, deterministic explanation rationale
- SYSTEM_DESIGN.md updated: `DailyGem` schema diagram, `get_daily_gem` data flow with explanation step, `add_track_to_liked` side-effect note, Score Breakdown API contract

**Addresses:** Per-recommendation outcome logging (PROJECT.md target), compound metric visibility

**Research flag:** No — docs update, no novel patterns.

---

### Phase Ordering Rationale

- Migration before view code: hard DB dependency; the view cannot write to columns that do not exist
- Backend before frontend: `explanation_data` must exist in the API response before the React component can consume it
- Compound metric write (Phase 2) before compound metric display (Phase 4): the `add_track_to_liked` annotation and the `MetricsStrip` render are independent; wiring the write first means data accumulates before the display is built
- Docs in Phase 4, not Phase 1: project memory requires CONCEPTS.md + SYSTEM_DESIGN.md updates with every code change; doing this after implementation ensures the docs are accurate

---

### Research Flags

**Phases needing deeper research during planning:** None. All patterns are confirmed from direct codebase inspection. The Spotify API constraints are verified against official changelogs. This is a well-bounded brownfield change with no unknowns.

**Phases with standard patterns (no research-phase needed):**
- Phase 1: Standard `AddField` Django migration
- Phase 2: Standard Django view extension with pure Python helpers
- Phase 3: Standard React component addition with Tailwind
- Phase 4: Standard metrics query extension + markdown doc update

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Direct codebase inspection; all dependencies confirmed installed; Spotify API status verified against official changelogs |
| Features | HIGH | Feature decisions grounded in ACM RecSys research + Spotify API constraints + PROJECT.md requirements |
| Architecture | HIGH | All architectural findings derived from specific file/line references in the existing codebase |
| Pitfalls | HIGH | Every pitfall cites specific view line numbers and tested code paths — not general domain knowledge |

**Overall confidence: HIGH**

### Gaps to Address

- **Source field on cached branch:** ARCHITECTURE.md notes that `source` in `score_breakdown` is on `RecommendationLog`, not `DailyGem`. The cached branch cannot reconstruct the source without a join through `Track`. Decision needed during Phase 1 planning: add `source_at_recommendation` CharField to `DailyGem` in the migration, or accept that source tag is only available on fresh-branch gems. Recommendation: add the CharField — one nullable column, enables per-source win rate analysis in the evaluation dashboard milestone.

- **Compound metric definition (OR vs AND):** FEATURES.md recommends `was_liked OR was_saved` (OR logic); ARCHITECTURE.md uses AND. OR is more correct at this scale — a single daily gem requiring both actions on the same day creates too sparse a label. Document the OR choice explicitly in CONCEPTS.md and in the metrics view query comment.

- **Bandit feedback closure (deferred to v1.2):** Thompson Sampling source stats (`source_stats[source]['s']`) are currently incremented only on LIKE, not on compound success. Feeding the compound metric back to the bandit requires `DailyGem.source` (not yet present) and a clear attribution path. Out of scope for v1.1 — flag as a v1.2 target for the evaluation dashboard milestone.

- **`was_played` field (deferred):** PITFALLS recommends adding `was_played` + a `POST /api/gem/played/` endpoint to track preview plays. Spotify deprecated `preview_url` on many tracks, making this signal fragile. Defer to the evaluation dashboard milestone when signal quality can be assessed against actual data.

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)

- `backend/apps/recommendations/hybrid_recommendation_engine.py` — score formula, `score_breakdown` structure, Thompson Sampling bandit, source multiplier location
- `backend/apps/core/models.py` — `DailyGem`, `RecommendationLog`, `UserFeedback`, `UserProfile` field inventory
- `backend/apps/core/views.py` — `get_daily_gem` (all three return sites), `add_track_to_liked`, `submit_feedback`, `get_recommendation_metrics`
- `frontend/app/profile/components/DailyGem/DailyGem.tsx` — `DailyGemResponse` interface, render logic
- `backend/apps/core/migrations/` (0001–0007) — migration history, existing column provenance
- `frontend/package.json` — installed frontend dependencies

### Primary (HIGH confidence — official changelogs)

- [Spotify Web API Changelog — February 2026](https://developer.spotify.com/documentation/web-api/references/changes/february-2026) — `GET /me/library/contains` replaces `GET /me/tracks/contains`
- [Introducing Changes to the Web API — November 2024](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api) — `audio-features`, `recommendations` removed

### Secondary (MEDIUM confidence — community + research papers)

- Spotify Developer Community — February 2026 API thread — playback API Premium restrictions confirmed
- "Explainability in music recommender systems" — Afchar, Wiley AI Magazine 2022 — simple/conclusive explanations score highest on user trust
- "A Comparative Analysis of Text-Based Explainable Recommender Systems" — ACM RecSys 2024 — text + visual hybrid > either alone
- "Characterisation of explicit feedback in an online music recommendation service" — ACM RecSys 2010 — saves are 3x stronger signal than plays

---

*Research completed: 2026-05-13*
*Ready for roadmap: yes*
