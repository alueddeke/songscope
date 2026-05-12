# Phase 4: Metrics, Evaluation & Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 04-metrics-evaluation-documentation
**Areas discussed:** Metrics persistence strategy, Chart library & visualization placement, Documentation scope & format, Diversity score definition

---

## Metrics Persistence Strategy

### Q1 — Persistence approach

| Option | Description | Selected |
|--------|-------------|----------|
| On-the-fly only | No new columns — compute from existing RecommendationLog + DailyGem at query time | ✓ |
| Persist new columns | Add like_rate, novelty_score, genre_diversity_score to DailyGem (migration required) | |
| Hybrid | Persist only diversity_score; compute rest on-the-fly | |

**User's choice:** On-the-fly only
**Notes:** Avoids migration, simpler, existing data is sufficient.

### Q2 — Endpoint structure

| Option | Description | Selected |
|--------|-------------|----------|
| Implement as-is, trend data separate | Match existing MetricsStrip interface; trend hits /api/recommendation-trend/ | ✓ |
| Add trend data to same response | Extend /api/recommendation-metrics/ with trend[] array | |

**User's choice:** Separate endpoints

### Q3 — Before/after comparison definition

| Option | Description | Selected |
|--------|-------------|----------|
| First 7 gems vs most recent 7 gems | Simple, self-explanatory learning curve story | ✓ |
| Fixed time split (30 days vs 30 days) | More robust, but portfolio unlikely to have 60 days of usage | |
| You decide | Leave to planner | |

**User's choice:** First 7 vs last 7

---

## Chart Library & Visualization Placement

### Q1 — Chart library

| Option | Description | Selected |
|--------|-------------|----------|
| Recharts | Most popular React chart library, SSR-safe, handles line + bar charts | ✓ |
| Custom CSS bars only | Zero new dependencies, limited to static bars | |
| Chart.js via react-chartjs-2 | Alternative, more config, less idiomatic in React | |

**User's choice:** Recharts

### Q2 — Visualization placement

| Option | Description | Selected |
|--------|-------------|----------|
| Below MetricsStrip, above DailyGem | Metrics context first, then gem | |
| Below DailyGem, above TopArtists | Gem is hero | |
| New section at bottom of page | Keeps hero area clean; charts accessible by scrolling | ✓ |

**User's choice:** New section at bottom

### Q3 — Taste profile chart display

| Option | Description | Selected |
|--------|-------------|----------|
| Top 10 genres, normalized to percentage | Readable, removes arbitrary count scale | ✓ |
| Top 5 genres, raw counts | Simpler, shows actual update increments | |
| All genres, normalized | Complete but potentially noisy | |

**User's choice:** Top 10 genres, normalized to percentage

---

## Documentation Scope & Format

### Q1 — Relationship to existing INTERVIEW_PREP_SONGSCOPE.md

| Option | Description | Selected |
|--------|-------------|----------|
| Supersede | Replace INTERVIEW_PREP with CONCEPTS.md + SYSTEM_DESIGN.md | |
| Complement | Keep INTERVIEW_PREP; add CONCEPTS.md + SYSTEM_DESIGN.md as new docs | ✓ |
| Consolidate | Merge everything into one CONCEPTS.md | |

**User's choice:** Complement — three docs coexist at repo root

### Q2 — File location

| Option | Description | Selected |
|--------|-------------|----------|
| Repo root | Visible immediately on GitHub; INTERVIEW_PREP is already there | ✓ |
| /docs/ subdirectory | Cleaner root but requires one more click | |
| backend/ root | Co-located with Python code but hidden from casual browsing | |

**User's choice:** Repo root

### Q3 — Architecture diagram format

| Option | Description | Selected |
|--------|-------------|----------|
| Mermaid diagram | Renders natively on GitHub, maintainable | ✓ |
| ASCII art | Works everywhere, less readable for complex flows | |
| Both: Mermaid + prose | Best of both worlds | |

**User's choice:** Mermaid

### Q4 — CONCEPTS.md depth

| Option | Description | Selected |
|--------|-------------|----------|
| Intuition + formula + code snippet | Interview sweet spot — covers whiteboard and code questions | ✓ |
| Formula only (no code) | Lighter, more academic | |
| Plain English only (no math) | Accessible but undersells technical depth | |

**User's choice:** Intuition + formula + code snippet

---

## Diversity Score Definition

### Q1 — Session window

| Option | Description | Selected |
|--------|-------------|----------|
| Rolling 7-day window | Matches trend chart window | |
| All-time | Total genre spread since day one | ✓ |
| Last 10 recommendations | Count-based, stable with irregular usage | |

**User's choice:** All-time

### Q2 — Distance formula

| Option | Description | Selected |
|--------|-------------|----------|
| Jaccard distance | 1 - \|A∩B\|/\|A∪B\| — standard set similarity, interview-friendly | ✓ |
| Unique genre count / total genres | Simpler, no pairwise computation | |
| You decide | Either Jaccard or unique-count | |

**User's choice:** Jaccard distance

### Q3 — Aggregation method

| Option | Description | Selected |
|--------|-------------|----------|
| Mean pairwise Jaccard distance | Average all N*(N-1)/2 pairwise distances — single interpretable number | ✓ |
| Median pairwise distance | More robust to outliers | |
| You decide | Mean vs median is a planner detail | |

**User's choice:** Mean pairwise Jaccard distance

---

## Claude's Discretion

- Exact Recharts component API choices (color theme should match existing `text-green` accent)
- Whether `/api/recommendation-trend/` returns daily or per-gem data points
- Cold-start handling when fewer than 7 gems exist
- Whether diversity score appears in MetricsStrip or only in the new bottom section

## Deferred Ideas

- Security hardening (SECRET_KEY rotation, CSRF, client secret) — explicitly out of scope per PROJECT.md
- Collaborative filtering metrics — no user base yet
- Audio feature weights revival — deferred from Phase 3, still deferred
- A/B testing infrastructure — ROADMAP introduces concept but implementing is out of Phase 4 scope
