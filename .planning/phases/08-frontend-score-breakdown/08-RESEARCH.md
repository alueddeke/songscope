# Phase 8: Frontend Score Breakdown — Research

**Researched:** 2026-05-19
**Domain:** Next.js 14 / React 18 / Tailwind CSS — pure frontend rendering, no new backend work
**Confidence:** HIGH

---

## Summary

Phase 8 is a pure frontend rendering task. Both data fields (`score_breakdown` and `compound_hit_rate`) are already present in the API responses from Phase 7. The only work is updating two TypeScript interfaces to expose the new fields, creating one sub-component (`ScoreBreakdown.tsx`), and making one stat swap in `MetricsStrip.tsx`.

The entire phase works within the existing stack: Next.js 14, React 18, Tailwind CSS 3.4. No new packages are needed. No new API calls are added — both target components consume data from existing `useEffect` fetches. The design contract is fully specified in `08-UI-SPEC.md`, so the planner's job is to sequence file modifications correctly, not to resolve any design ambiguity.

The one structural concern worth noting: the frontend currently has a pre-existing TypeScript build error in `TopArtists.tsx` (unrelated to this phase). The phase executor must not introduce additional type errors, and the plan should note this pre-existing issue so it is not mistakenly attributed to phase work.

**Primary recommendation:** Create `ScoreBreakdown.tsx` as a standalone sub-component (established pattern, mirrors `FeedbackButtonGroup`), update two TypeScript interfaces, insert the component in `DailyGem.tsx`, and swap the stat in `MetricsStrip.tsx`. Four discrete file changes with no inter-dependencies.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Score bars appear directly below the explanation blockquote — natural reading flow (why in words → why in numbers). Placed before the audio preview section.
- **D-02:** If `score_breakdown` is empty or missing (pre-migration rows), hide bars entirely — no placeholder, no message, no greyed-out state. The explanation text still renders if present.
- **D-03:** All 3 bars use single color — `bg-green` fill on `bg-gray-800` track. No per-component color differentiation. Consistent with Spotify green accent used throughout the app.
- **D-04:** Layout: label left, percentage right, bar full-width between. Each row: `[Label] [bar] [XX%]`.
- **D-05:** Percentages rounded to the nearest 5% (per ROADMAP.md success criterion). Formula: `Math.round(value * 100 / 5) * 5`.
- **D-06:** Bar labels: "Genre Match", "Novelty", "Feedback" (short, fits single line).
- **D-07:** Replace "Acceptance rate" `<Stat>` tile with "Hit rate". The `gem_acceptance_rate` stat is removed from the displayed strip; `compound_hit_rate` takes its slot.
- **D-08:** Display label: "Hit rate" (lowercase, matches existing label style: "Gems shown", "Hidden gem rate").
- **D-09:** Value format: `${Math.round(compound_hit_rate * 100)}%` — same pattern as existing acceptance rate rendering.
- **D-10:** `DailyGemResponse` interface in `DailyGem.tsx` needs `score_breakdown: Record<string, number>` added (optional or defaulting to `{}`).
- **D-11:** `Metrics` interface in `MetricsStrip.tsx` needs `compound_hit_rate: number | null` added; `gem_acceptance_rate` can remain for type safety but won't be displayed.

### Claude's Discretion

- Exact Tailwind classes for bar height, corner radius, and label/value typography (consistent with surrounding text scale)
- Whether score bars are extracted into a `ScoreBreakdown.tsx` sub-component or inlined in `DailyGem.tsx` (follow existing pattern — `FeedbackButtonGroup` is a separate file; if bars are >20 lines, extract)
- Whether the bar container has a border/background or sits flush (match existing blockquote and section visual weight)

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXPLAIN-03 | Frontend gem card shows 3 labeled score bars (Genre Match %, Novelty %, Feedback influence %) rendered from `score_breakdown` data returned by the `get_daily_gem` API | Data already returned by API (Phase 7 complete). `ScoreBreakdown.tsx` sub-component renders bars from `gem.score_breakdown`. Interface update in `DailyGem.tsx` exposes the field. |
| METRIC-03 | `MetricsStrip` UI displays compound hit rate alongside existing `gem_acceptance_rate` | `compound_hit_rate` already returned by `/api/recommendation-metrics/` (Phase 7 complete). Stat swap in `MetricsStrip.tsx` + interface update. |

</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Score bar rendering | Browser / Client | — | Pure display component; reads from existing React state (`gem.score_breakdown`); no server round-trip |
| Rounding formula (nearest 5%) | Browser / Client | — | Pure math transformation at render time; `Math.round(value * 100 / 5) * 5` |
| Empty state guard | Browser / Client | — | `Object.keys(breakdown).length === 0` check in `ScoreBreakdown`; returns `null` |
| Compound hit rate display | Browser / Client | — | Reads `metrics.compound_hit_rate` from existing `fetchMetrics()` state; no new fetch |
| `score_breakdown` data source | API / Backend | — | Already wired in Phase 7 `get_daily_gem` view; field present in JSON response |
| `compound_hit_rate` data source | API / Backend | — | Already wired in Phase 7 `get_recommendation_metrics` view; field always present |
| TypeScript interface definitions | Browser / Client | — | Co-located with component files per established project pattern |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 14.2.4 | App framework, `"use client"` boundary | Already in use; target components are client components |
| React | 18.x | Component model, `useState`/`useEffect` | Already in use; no new hooks needed for this phase |
| TypeScript | 5.x | Interface definitions | All existing components are typed; interfaces must be updated |
| Tailwind CSS | 3.4.1 | Utility classes for bar layout | Already in use; `bg-green`, `bg-gray-800`, `rounded-full`, `h-2`, `flex`, `flex-1` cover all required styles |

[VERIFIED: codebase — package.json in /Users/antonilueddeke/Desktop/Projects/songscope/frontend/package.json]

### No New Dependencies Required

No npm installs are needed for this phase. All styling is achievable with Tailwind utility classes already configured in `tailwind.config.ts`. No component library, no animation library, no charting library.

[VERIFIED: codebase — tailwind.config.ts confirms `green: "#1DB954"` custom color token]

---

## Architecture Patterns

### System Architecture Diagram

```
GET /api/daily-gem/
        |
        v
  DailyGem.tsx (fetchGem)
  setGem(data) — data.score_breakdown: Record<string,number>
        |
        v
  gem.score_breakdown ──> ScoreBreakdown.tsx
                              |
                              ├── Object.keys(breakdown).length === 0 → return null
                              |
                              └── Map [genre_sim, novelty, feedback_multiplier]
                                      → row: label | bar | pct


GET /api/recommendation-metrics/
        |
        v
  MetricsStrip.tsx (fetchMetrics)
  setMetrics(data) — data.compound_hit_rate: number | null
        |
        v
  metrics.compound_hit_rate ──> <Stat label="Hit rate" value={hitRate} />
```

### Recommended Project Structure

```
frontend/app/profile/components/
├── DailyGem/
│   ├── DailyGem.tsx          # modified — add score_breakdown to DailyGemResponse; import + render ScoreBreakdown
│   └── ScoreBreakdown.tsx    # new — sub-component for 3-bar score display
└── MetricsStrip/
    └── MetricsStrip.tsx      # modified — add compound_hit_rate to Metrics; replace Acceptance rate stat
```

### Pattern 1: Sub-Component Extraction (ScoreBreakdown)

**What:** Extract score bar rendering into a named sub-component file, following the `FeedbackButtonGroup` precedent.
**When to use:** When a logical display block exceeds ~20 lines and has a single coherent responsibility.
**Example:**

```typescript
// Source: VERIFIED from codebase — mirrors FeedbackButtonGroup.tsx pattern
// frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx
"use client";

interface ScoreBreakdownProps {
  breakdown: Record<string, number>;
}

const SCORE_ROWS: { key: string; label: string }[] = [
  { key: "genre_sim",           label: "Genre Match" },
  { key: "novelty",             label: "Novelty"     },
  { key: "feedback_multiplier", label: "Feedback"    },
];

export default function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  if (Object.keys(breakdown).length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      {SCORE_ROWS.map(({ key, label }) => {
        const raw = breakdown[key] ?? 0;
        const pct = Math.round(raw * 100 / 5) * 5;
        return (
          <div key={key} className="flex items-center gap-2">
            <span className="text-sm text-gray-300 w-28 flex-shrink-0">{label}</span>
            <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
              <div className="bg-green rounded-full h-full" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-sm font-bold text-gray-300 w-9 text-right flex-shrink-0">{pct}%</span>
          </div>
        );
      })}
    </div>
  );
}
```

[VERIFIED: CONTEXT.md D-01 through D-06, D-10; UI-SPEC.md ScoreBreakdown render contract]

### Pattern 2: Conditional Rendering Guard

**What:** Use `{condition && (<Component />)}` — same as existing `explanation` blockquote guard.
**When to use:** When a section should not render at all (not just be hidden) when data is absent.
**Example:**

```typescript
// Source: VERIFIED — DailyGem.tsx line 150 existing pattern
{explanation && (
  <blockquote className="border-l-2 border-green pl-4 py-1">
    <p className="text-gray-300 italic text-sm leading-relaxed">{explanation}</p>
  </blockquote>
)}

// New pattern — same idiom, ScoreBreakdown returns null internally
<ScoreBreakdown breakdown={gem.score_breakdown ?? {}} />
```

[VERIFIED: codebase — DailyGem.tsx lines 150-154]

### Pattern 3: Stat Swap in MetricsStrip

**What:** Replace one `<Stat>` call, add `hitRate` derivation variable, update interface.
**When to use:** When a displayed metric changes but the `<Stat>` component contract is unchanged.
**Example:**

```typescript
// Source: VERIFIED — MetricsStrip.tsx lines 56-59, 67 (existing acceptance pattern)

// Interface update
interface Metrics {
  // ... existing fields unchanged ...
  gem_acceptance_rate: number | null; // keep for type safety
  compound_hit_rate: number | null;   // add
}

// Derivation (replace `acceptance` variable, or add `hitRate` alongside)
const hitRate =
  metrics.compound_hit_rate !== null
    ? `${Math.round(metrics.compound_hit_rate * 100)}%`
    : "—";

// JSX — replace
// <Stat label="Acceptance rate" value={acceptance} />
// with:
<Stat label="Hit rate" value={hitRate} />
```

[VERIFIED: codebase — MetricsStrip.tsx lines 56-67]

### Anti-Patterns to Avoid

- **Inline score bars in DailyGem.tsx:** The resulting JSX block exceeds 20 lines (3 rows × 6+ elements each). Extract to `ScoreBreakdown.tsx` per the `FeedbackButtonGroup` pattern. [VERIFIED: codebase — FeedbackButtonGroup is a separate file]
- **Guarding outside the component:** Do not put `{breakdown && Object.keys(breakdown).length > 0 && <ScoreBreakdown ... />}` in `DailyGem.tsx`. Put the guard inside `ScoreBreakdown` (returns `null`). Keeps `DailyGem.tsx` clean and matches how `AudioPlayer` handles its own conditional logic.
- **Using `inline-block` + `width` on a div:** Use `flex-1` on the track wrapper and `style={{ width: '${pct}%' }}` on the fill div — not absolute positioning. Ensures responsiveness and correct reflow. [ASSUMED — standard Tailwind progress bar pattern]
- **Removing `gem_acceptance_rate` from the interface:** D-11 states keep it for type safety. The backend still returns it; removing the type would require a non-null cast elsewhere. Leave the field in the interface, just don't render it.
- **Deriving `score_breakdown` from `gem` before null check:** `DailyGem.tsx` already guards `if (!gem)` before destructuring. The destructure `const { track, explanation, date } = gem` happens after the null guard. Add `score_breakdown` to the destructure at the same line, not before the guard.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bar | Custom SVG / Canvas bar | Tailwind `div` with `style={{ width }}` | Zero dependency; Tailwind's `rounded-full`, `h-2`, `overflow-hidden` fully cover the visual spec |
| Percentage formatting | Custom formatter | `Math.round(x * 100 / 5) * 5` inline | Formula is two operations; no utility function needed |
| Null-safe metric rendering | Custom loading skeleton | `null \| "—"` ternary | Existing `MetricsStrip` already uses this pattern for `gem_acceptance_rate` |

**Key insight:** This phase is intentionally small — the complexity was handled in Phase 7 (backend wiring). The frontend work is 4 file changes and no new packages.

---

## Runtime State Inventory

> Phase 8 is a greenfield rendering phase — no renaming, no migration. Omitted per instructions.

---

## Common Pitfalls

### Pitfall 1: `score_breakdown` Destructure Before Null Guard

**What goes wrong:** TypeScript error — `gem` could be `null` at destructure site.
**Why it happens:** Developer adds `score_breakdown` to the destructure line but the existing code only destructures `{ track, explanation, date }` after the null-guard block.
**How to avoid:** Add `score_breakdown` to the existing destructure at line 91: `const { track, explanation, date, score_breakdown } = gem;`
**Warning signs:** TypeScript error `Property 'score_breakdown' does not exist on type 'DailyGemResponse'` — means the interface wasn't updated first.

[VERIFIED: codebase — DailyGem.tsx line 91]

### Pitfall 2: `compound_hit_rate` Key Missing at Runtime for Old Metrics Responses

**What goes wrong:** `metrics.compound_hit_rate` is `undefined` (not `null`) on older cached responses — the null check `!== null` passes, but `Math.round(undefined * 100)` returns `NaN`, which renders as an empty string.
**Why it happens:** The field is new; any cached or pre-Phase-7 API response won't include it.
**How to avoid:** Use nullish coalescing: `metrics.compound_hit_rate ?? null` when assigning, or guard with `typeof metrics.compound_hit_rate === 'number'`. The `"—"` fallback already covers `null`; extend it to cover `undefined` by using `metrics.compound_hit_rate != null` (double-not-equal).
**Warning signs:** MetricsStrip shows "NaN%" for hit rate.

[VERIFIED: CONTEXT.md — Phase 7 D-12 confirms `compound_hit_rate` always present, but defensive coding is warranted for pre-phase-7 test data]

### Pitfall 3: Pre-Existing Build Error Masking New TypeScript Errors

**What goes wrong:** `npm run build` reports the existing `TopArtists.tsx` type error and stops. Developer assumes their changes caused it.
**Why it happens:** `TopArtists.tsx` has a pre-existing `TS2345` error (line 85) that is unrelated to this phase.
**How to avoid:** Baseline the error before starting: `npx tsc --noEmit` confirms exactly one pre-existing error. Any new errors after phase work are attributable to this phase.
**Warning signs:** Build failure citing `TopArtists.tsx:85` — this is pre-existing and not caused by phase work.

[VERIFIED: codebase — confirmed via `npx tsc --noEmit` baseline run]

### Pitfall 4: Bar Width at 0% and 100%

**What goes wrong:** A bar fill div with `width: 0%` inside a `overflow-hidden` parent still renders as a 0px box that can affect layout. A 100% bar may overflow if padding is added.
**Why it happens:** Tailwind's `overflow-hidden` on the track div and `rounded-full` on the fill div requires the fill to be a child with `h-full` — otherwise the rounding clips incorrectly.
**How to avoid:** Use `style={{ width: \`${pct}%\` }}` on the fill div (child), `overflow-hidden` on the track div (parent). The `h-full` on the fill div makes it fill the track height. This is the spec from UI-SPEC.md and has been confirmed as the correct pattern.
**Warning signs:** Bars with 0% show visual artifacts; bars with 100% clip at the rounded corners.

[VERIFIED: UI-SPEC.md — render contract specifies exactly this structure]

### Pitfall 5: Key Ordering in Score Rows

**What goes wrong:** Using `Object.keys(breakdown)` to iterate produces bars in insertion order — which may not match the "Genre Match, Novelty, Feedback" display order.
**Why it happens:** The API returns a dict; Python dict insertion order is consistent but not guaranteed to match the desired display order.
**How to avoid:** Use a fixed-order constant array (as shown in the Pattern 1 code example): `const SCORE_ROWS = [{ key: 'genre_sim', label: 'Genre Match' }, ...]`. Never iterate `Object.keys(breakdown)` directly.
**Warning signs:** Bar order changes between page loads or environments.

[VERIFIED: UI-SPEC.md render contract — "Render exactly 3 rows in this fixed order"]

---

## Code Examples

### ScoreBreakdown.tsx — Full Component

```typescript
// Source: VERIFIED — synthesized from UI-SPEC.md render contract + DailyGem.tsx patterns
"use client";

interface ScoreBreakdownProps {
  breakdown: Record<string, number>;
}

const SCORE_ROWS: { key: string; label: string }[] = [
  { key: "genre_sim",           label: "Genre Match" },
  { key: "novelty",             label: "Novelty"     },
  { key: "feedback_multiplier", label: "Feedback"    },
];

export default function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  if (Object.keys(breakdown).length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      {SCORE_ROWS.map(({ key, label }) => {
        const raw = breakdown[key] ?? 0;
        const pct = Math.round(raw * 100 / 5) * 5;
        return (
          <div key={key} className="flex items-center gap-2">
            <span className="text-sm text-gray-300 w-28 flex-shrink-0">{label}</span>
            <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
              <div className="bg-green rounded-full h-full" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-sm font-bold text-gray-300 w-9 text-right flex-shrink-0">{pct}%</span>
          </div>
        );
      })}
    </div>
  );
}
```

### DailyGem.tsx — Interface Update + Import + Usage

```typescript
// Source: VERIFIED — DailyGem.tsx current state; changes are additive

// 1. Interface update (line 21)
interface DailyGemResponse {
  track: GemTrack;
  explanation: string;
  score_breakdown: Record<string, number>; // ADD THIS
  date: string;
  cached: boolean;
}

// 2. Import (add alongside FeedbackButtonGroup import)
import ScoreBreakdown from "./ScoreBreakdown";

// 3. Destructure (line 91)
const { track, explanation, date, score_breakdown } = gem;

// 4. JSX — insert after explanation blockquote (line 154), before audio preview (line 157)
<ScoreBreakdown breakdown={score_breakdown ?? {}} />
```

### MetricsStrip.tsx — Interface Update + Stat Swap

```typescript
// Source: VERIFIED — MetricsStrip.tsx current state; changes are minimal

// 1. Interface update (line 6)
interface Metrics {
  // ... all existing fields ...
  gem_acceptance_rate: number | null; // KEEP — type safety
  compound_hit_rate: number | null;   // ADD
}

// 2. Derivation (replace or add alongside existing `acceptance` variable)
const hitRate =
  metrics.compound_hit_rate != null
    ? `${Math.round(metrics.compound_hit_rate * 100)}%`
    : "—";

// 3. JSX — replace (line 67)
// REMOVE: <Stat label="Acceptance rate" value={acceptance} />
// ADD:
<Stat label="Hit rate" value={hitRate} />
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CSS `width` with inline styles on progress bars | Same — still standard | N/A | `style={{ width }}` is the correct approach for dynamic widths not known at build time; Tailwind arbitrary values `w-[${pct}%]` are not viable for runtime-computed values |
| Custom progress bar components (e.g., rc-progress) | Tailwind div approach | N/A | No dependency needed for a single-color filled bar |

**No deprecated patterns apply.** This phase uses the most straightforward possible approach: a div with an inline width style inside an overflow-hidden container.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Using `style={{ width: '${pct}%' }}` on the fill div with `overflow-hidden` on the track produces correct visual rounding behavior | Code Examples / Anti-Patterns | Bar corners may clip incorrectly; fix: remove `rounded-full` from fill div and only apply to track |
| A2 | `FeedbackButtonGroup` pattern (separate file per sub-component) is the consensus extraction threshold for this codebase | Architecture Patterns | Minor: bars could instead be inlined; no functional impact |

**All other claims were verified against the codebase or CONTEXT.md/UI-SPEC.md.**

---

## Open Questions

1. **Pre-existing TypeScript build error in TopArtists.tsx**
   - What we know: `TopArtists.tsx:85` has a `TS2345` type error present before this phase starts.
   - What's unclear: Was this intentionally left unfixed, or is it blocking CI?
   - Recommendation: Phase executor should note the error, verify it is pre-existing via `npx tsc --noEmit` before starting, and not attempt to fix it as part of this phase's scope.

---

## Environment Availability

> Step 2.6: All dependencies are in-repo npm packages already installed. No external tools, runtimes, databases, or CLI utilities are required beyond `node` (already available). Skipped with reason: no new external dependencies introduced.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None — no frontend test framework configured |
| Config file | No `jest.config.*` or `vitest.config.*` found in `/frontend/` |
| Quick run command | N/A |
| Full suite command | `cd frontend && npm run build` (type check via `tsc --noEmit` + Next.js build) |

No Jest, Vitest, or React Testing Library found in `package.json`. The frontend has no automated unit test suite. [VERIFIED: codebase scan — only test files found are inside `node_modules/`]

The backend pytest suite is unaffected by this phase (141 tests, all pass — verified baseline).

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Infrastructure Exists? |
|--------|----------|-----------|-------------------|----------------------|
| EXPLAIN-03 | Score bars render from `score_breakdown`; empty state renders null | Visual / Manual | `cd frontend && npx tsc --noEmit` (type check); visual verification in browser | No unit tests — Wave 0 gap |
| EXPLAIN-03 | Rounding formula: `Math.round(0.72 * 100 / 5) * 5 === 70` | Unit logic | Verifiable inline during code review | No test file |
| METRIC-03 | "Hit rate" stat renders; `compound_hit_rate: null` shows "—" | Visual / Manual | `cd frontend && npx tsc --noEmit` | No unit tests — Wave 0 gap |

### Sampling Rate

- **Per task commit:** `cd frontend && npx tsc --noEmit` — catches interface mismatches
- **Per wave merge:** `cd frontend && npm run build` — full Next.js compile + type check
- **Phase gate:** `npm run build` succeeds (with the known pre-existing TopArtists error excluded from blame) + manual browser verification of bars and hit rate tile

### Wave 0 Gaps

- [ ] No frontend test framework configured. For a phase this small (4 file changes, no logic beyond a rounding formula), this is acceptable — manual browser verification is the stated gate.
- [ ] If a test is desired for the rounding formula: a plain `.test.ts` file with `npx tsx` would work without a full test framework setup. **Not blocking.**

*(Backend: no gaps — 141 tests pass, backend unchanged in this phase)*

---

## Security Domain

> Phase 8 is a read-only frontend rendering phase. It displays data already returned by authenticated API endpoints (no new endpoints, no new auth surfaces, no input handling, no form submission). No new ASVS categories apply.

| ASVS Category | Applies | Note |
|---------------|---------|------|
| V2 Authentication | No | No auth changes |
| V3 Session Management | No | No session changes |
| V4 Access Control | No | No new routes or permissions |
| V5 Input Validation | No | No user input — display-only component |
| V6 Cryptography | No | No crypto |

Score bars and hit rate are read-only display elements populated from existing authenticated fetches. The `score_breakdown` values are server-computed floats — they are rendered directly without sanitization risk (numeric, no HTML injection surface).

---

## Sources

### Primary (HIGH confidence)
- `frontend/app/profile/components/DailyGem/DailyGem.tsx` — current component structure, existing patterns, interface, destructure sites
- `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` — existing `Metrics` interface, `<Stat>` component, acceptance rate rendering pattern
- `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx` — sub-component extraction pattern
- `frontend/tailwind.config.ts` — confirmed `green: "#1DB954"` token, no other relevant tokens
- `frontend/package.json` — confirmed Next.js 14.2.4, React 18, TypeScript 5, Tailwind 3.4.1
- `.planning/phases/08-frontend-score-breakdown/08-CONTEXT.md` — all locked decisions D-01 through D-11
- `.planning/phases/08-frontend-score-breakdown/08-UI-SPEC.md` — full render contract, spacing, typography, color

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — EXPLAIN-03, METRIC-03 exact acceptance criteria
- `.planning/STATE.md` — phase context and prior decisions
- `npx tsc --noEmit` output — confirmed single pre-existing error in `TopArtists.tsx`, no errors in target components

### Tertiary (LOW confidence)
- None — all claims are codebase-verified.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — confirmed from `package.json` and `tailwind.config.ts`
- Architecture: HIGH — confirmed from direct codebase inspection; no ambiguity in component structure
- Pitfalls: HIGH — derived from actual code at modification sites; TypeScript baseline confirmed via `tsc --noEmit`
- Design spec: HIGH — fully specified in `08-UI-SPEC.md`; no discretionary design decisions remain unresolved

**Research date:** 2026-05-19
**Valid until:** 2026-07-19 (stable stack; dependencies are pinned)
