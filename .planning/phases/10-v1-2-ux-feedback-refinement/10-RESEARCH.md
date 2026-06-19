# Phase 10: v1.2 UX & Feedback Refinement — Research

**Researched:** 2026-06-19
**Domain:** React/Next.js App Router state management, Python/Django AI prompt engineering, Tailwind CSS
**Confidence:** HIGH

---

## Summary

Phase 10 is a pure UI/wiring phase — no new dependencies, no new API endpoints, no database changes. All 9 requirements (SYNC-01 through UI-04) are surgical edits to files that were read directly during research. Confidence is HIGH because every finding is grounded in the actual file contents, not documentation inference.

The three themes have different risk profiles. The AI Feedback ↔ Thumbs Sync cluster (SYNC-01–03) requires the most careful thinking: the `onFeedbackSubmitted` callback in `DailyGem.tsx` currently has signature `() => void` (it just sets modal state), but SYNC-03 requires it to receive the AI interpretation object. That is a signature change that must propagate through `AIFeedbackInput.tsx`'s props — but `AIFeedbackInput` already passes `(response.interpretation)` to the callback, so the **receiving side** is already correct and only the **declaration side** in DailyGem needs to change. The Taste Evolution Live Refresh cluster (EVOLVE-01–02) uses the `window.CustomEvent` pattern, which is safe in Next.js App Router because both components are `"use client"` — there is no SSR hazard. The Profile UI Quality cluster (UI-01–04) is the lowest risk: mechanical removals and string/class swaps with no behavioral logic changes.

**Primary recommendation:** Implement in two waves. Wave 1: SYNC-01 (backend prompt) + all UI changes (UI-01–04) — these are independent and low-risk. Wave 2: SYNC-02/03 + EVOLVE-01/02 — these involve state threading across components and should be verified together. The CustomEvent approach is correct for EVOLVE; the controlled-prop approach is correct for SYNC.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| AI sentiment extraction | API/Backend | — | OpenAI call lives in `ai_feedback_service.py`; frontend only reads the result |
| Like/dislike toggle sync | Frontend (Client) | — | Pure visual state — no second API call, no server involvement |
| ImprovementStory live refresh | Frontend (Client) | — | Already calls `/api/recommendation-metrics/` directly; event just re-triggers existing fetch |
| Popularity label semantics | Frontend (Client) | — | Presentation logic only — `getPopularityColor` → `getPopularityLabel` |
| Section label copy | Frontend (Server) | — | `profile/page.tsx` is a Server Component; label changes are static string edits |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SYNC-01 | Add `overall_sentiment` field to `_build_prompt` JSON schema in `ai_feedback_service.py` | Schema already uses flat JSON; one new field added to both the schema block and the rules block. Fallback `_fallback_interpretation` needs a matching key added. |
| SYNC-02 | `FeedbackButtonGroup.tsx` accepts `syncedFeedback?: 'LIKE' \| 'DISLIKE' \| null` prop; mirrors it via `setSelectedFeedback` without API call | Component currently manages `selectedFeedback` as fully internal state. Adding a controlled prop requires a `useEffect` watching `syncedFeedback`. |
| SYNC-03 | `DailyGem.tsx` tracks `aiSyncedFeedback` state; wires `onFeedbackSubmitted` → `syncedFeedback` prop | `onFeedbackSubmitted` currently has signature `() => void`. Must become `(interpretation: any) => void`. `AIFeedbackInput` already calls `onFeedbackSubmitted?.(response.interpretation)` so it already passes the object. |
| EVOLVE-01 | `DailyGem.tsx` dispatches `window.dispatchEvent(new CustomEvent('songscope:new-gem'))` after `setGem(data)` | `fetchGem` is already defined; dispatch call goes inside the `setGem(data)` line's scope in the try block. |
| EVOLVE-02 | `ImprovementStory.tsx` adds `useEffect` listener for `'songscope:new-gem'` that calls `fetchMetrics()` | `ImprovementStory` currently calls the metrics fetch inline in a `useEffect`. Must be refactored to a named `fetchMetrics` function callable from both the mount effect and the event listener. |
| UI-01 | Remove "Refresh stats" button and `refreshing`/`setRefreshing` state from `MetricsStrip.tsx` | Button is at lines 89–95; `refreshing`/`setRefreshing` state at lines 32, 36, 45. `fetchMetrics` signature simplifies to `async () => void` (no `showRefreshing` param). |
| UI-02 | Replace `getPopularityColor` in `TopArtists.tsx` with `getPopularityLabel` returning `{ label, color }` using Hidden Gem / Rising / Mainstream tiers | Current function uses green=high popularity (semantically backwards). New tiers: < 40 → Hidden Gem / text-green, 40–69 → Rising / text-yellow-400, ≥ 70 → Mainstream / text-gray-400. |
| UI-03 | Replace `bg-gray-850` with `bg-gray-800` in expanded artist row container in `TopArtists.tsx` | `bg-gray-850` is not in Tailwind config (only `green: #1DB954` is custom). Standard Tailwind gray scale has 800 and 900 but not 850 — renders as no background. Line 190 of TopArtists.tsx. |
| UI-04 | Update section subtitle copy in `profile/page.tsx`: "Your taste profile" → "Your genre taste profile" | Line 83. "Like-rate trend (7-day rolling)" at line 79 is already correct — no change needed. |
</phase_requirements>

---

## Standard Stack

No new dependencies in this phase. All work uses existing project stack.

### Core (already installed)
| Library | Purpose | Phase usage |
|---------|---------|-------------|
| React 18 + Next.js App Router | Frontend framework | All SYNC / EVOLVE / UI changes |
| TypeScript | Type safety | Prop interface additions |
| Tailwind CSS (with custom green alias) | Styling | UI-02, UI-03 class replacements |
| OpenAI Python SDK | AI feedback | SYNC-01 prompt schema edit |
| Django | Backend framework | SYNC-01 lives in `ai_feedback_service.py` |

**No `npm install` or `pip install` steps required.**

---

## Package Legitimacy Audit

> SKIPPED — no new packages installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
[User types AI feedback]
         |
         v
AIFeedbackInput.tsx ──POST /api/submit-ai-feedback/──> ai_feedback_service.py
  calls onFeedbackSubmitted(interpretation)              _build_prompt adds overall_sentiment
         |                                               OpenAI returns {…, overall_sentiment}
         v
DailyGem.tsx (onFeedbackSubmitted handler)
  reads interpretation.overall_sentiment
  sets aiSyncedFeedback state ('LIKE'|'DISLIKE'|null)
  dispatches 'songscope:new-gem' CustomEvent (EVOLVE-01)
         |                          |
         v                          v
FeedbackButtonGroup.tsx     ImprovementStory.tsx
  receives syncedFeedback       listens for 'songscope:new-gem'
  mirrors visual toggle         calls fetchMetrics()
  (no API call)                 (no page reload)
```

### Pattern 1: Controlled Prop Sync for SYNC-02

**What:** Accept an external prop that overrides internal state when non-null, without giving the parent full control (component still manages its own API call).
**When to use:** When a sibling component can produce a signal that should reflect in another component's visual state, but the receiving component also has its own state management logic.

```typescript
// Source: [ASSUMED] — standard React controlled/uncontrolled hybrid pattern

// In FeedbackButtonGroup.tsx — add prop and sync effect
interface FeedbackButtonGroupProps {
  trackId: string;
  onTrackRemoved?: () => void;
  onDislike?: () => void;
  syncedFeedback?: 'LIKE' | 'DISLIKE' | null;  // NEW
}

// Inside component body — add effect after existing state declarations
useEffect(() => {
  if (syncedFeedback != null) {
    setSelectedFeedback(syncedFeedback);
  }
}, [syncedFeedback]);
```

**Why this pattern (not ref, not event):** The requirement explicitly specifies a prop. A prop makes the data flow explicit in JSX and testable. A ref would require the parent to imperatively call a method — harder to reason about. Another CustomEvent would couple the components indirectly and make the flow non-obvious.

**Key safety rule:** The `useEffect` guard `if (syncedFeedback != null)` is essential — if parent resets to `null` (e.g., on new gem load), it must NOT clear the user's manual like/dislike selection.

### Pattern 2: CustomEvent for EVOLVE-01/02

**What:** `window.dispatchEvent(new CustomEvent('songscope:new-gem'))` in `DailyGem.tsx`; `window.addEventListener('songscope:new-gem', handler)` in `ImprovementStory.tsx`.
**When to use:** Cross-component communication between components that are not in a parent-child relationship and share no common ancestor that can hold the state.

```typescript
// Source: [ASSUMED] — MDN CustomEvent + React useEffect cleanup pattern

// In DailyGem.tsx — inside fetchGem after setGem(data)
setGem(data);
window.dispatchEvent(new CustomEvent('songscope:new-gem'));

// In ImprovementStory.tsx — rename inline fetch to fetchMetrics function
const fetchMetrics = () => {
  get<MetricsResponse>("/api/recommendation-metrics/")
    .then((r) => setStory(r.improvement_story ?? null))
    .catch(() => {})
    .finally(() => setLoading(false));
};

useEffect(() => {
  fetchMetrics();  // initial load (existing behavior)
}, []);

useEffect(() => {
  const handler = () => fetchMetrics();
  window.addEventListener('songscope:new-gem', handler);
  return () => window.removeEventListener('songscope:new-gem', handler);  // cleanup
}, []);
```

**No SSR hazard:** Both `DailyGem.tsx` and `ImprovementStory.tsx` are `"use client"` components (confirmed by direct inspection). `window` is only accessed at runtime, not during server rendering.

**Cleanup requirement:** The `removeEventListener` in the effect cleanup is mandatory. Without it, each re-mount of `ImprovementStory` adds a new listener — memory leak and duplicate fetch calls.

### Pattern 3: SYNC-01 — Adding a Field to OpenAI JSON Schema

**What:** Add `overall_sentiment` to the JSON schema block in `_build_prompt` and the fallback `_fallback_interpretation` dict.

```python
# Source: [VERIFIED] — direct inspection of ai_feedback_service.py

# In _build_prompt — add to the JSON object template:
"overall_sentiment": "positive" | "negative" | "neutral" | null,

# In _build_prompt Rules section — add a rule:
# - Set overall_sentiment based on the general tone of the feedback:
#   "positive" if the user is satisfied/happy, "negative" if dissatisfied,
#   "neutral" if informational or mixed, null if unclear.

# In _fallback_interpretation — add to interpretation dict:
"overall_sentiment": None,
# Keyword matching for overall_sentiment:
if any(word in user_text_lower for word in ["love", "great", "amazing", "good", "like"]):
    interpretation["overall_sentiment"] = "positive"
elif any(word in user_text_lower for word in ["hate", "don't like", "awful", "bad", "dislike", "not"]):
    interpretation["overall_sentiment"] = "negative"
```

**Why the fallback must be updated:** SYNC-03 reads `interpretation.overall_sentiment` in `DailyGem.tsx`. If OpenAI is unavailable and the fallback doesn't have this key, `interpretation.overall_sentiment` is `undefined` (not `null`) in JavaScript after JSON serialization — the map in SYNC-03 will not fire correctly. Adding `overall_sentiment: None` to the fallback ensures the key is always present.

### Anti-Patterns to Avoid

- **Double API call:** SYNC-02 must NOT call `/api/submit-feedback/` when `syncedFeedback` prop changes. The requirement is visual toggle only. The existing `handleSubmit` path should only fire on user click.
- **Forgetting the null guard in SYNC-02:** If `syncedFeedback` prop resets to `null` after a new gem loads, the effect must not call `setSelectedFeedback(null)` — that would wipe out the user's explicit click state. Use `if (syncedFeedback != null)`.
- **Misidentifying UI-04 scope:** `page.tsx` line 79 already reads "Like-rate trend (7-day rolling)" — this is already correct. Only line 83 ("Your taste profile" → "Your genre taste profile") needs changing.
- **Using bg-gray-750 as a fix reference:** `bg-gray-750` is also not in the Tailwind config (same issue as bg-gray-850) and appears in the codebase as hover states in `TopArtists.tsx` and `ArtistExpandedDetails.tsx`. Do NOT treat bg-gray-750 as a model for "what exists" — it's a separate pre-existing issue outside Phase 10 scope. Only fix `bg-gray-850` per UI-03.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-component communication (EVOLVE) | Custom pub/sub system or shared context | `window.CustomEvent` | Both components are already client-only; CustomEvent is zero-dependency and works across the component tree without lifting state |
| AI response field presence guarantee | Frontend null-check gymnastics | Backend always returning `overall_sentiment` key (even as `null`) | The safest contract is the backend always serializes the key; frontend checks `=== 'positive'` not `?? null` |
| Sibling state sync | Redux or Zustand state slice | Controlled prop + `useEffect` | The scope is one visual toggle in one component; global state is engineering overkill |

---

## Common Pitfalls

### Pitfall 1: onFeedbackSubmitted Signature Mismatch

**What goes wrong:** `DailyGem.tsx` line 196 passes `onFeedbackSubmitted={() => setShowFeedbackModal(true)}` — a zero-argument callback. If the planner only adds `aiSyncedFeedback` state and wires the `syncedFeedback` prop without also updating this callback to receive the interpretation, the sync never fires.
**Why it happens:** The callback is declared inline as a no-arg arrow function. It looks complete. The new logic needs to be inserted into the same callback site.
**How to avoid:** Replace the inline arrow function with a named handler that both sets the modal state AND reads interpretation.overall_sentiment.
**Warning signs:** `aiSyncedFeedback` state exists but never changes from `null`.

**Correct pattern:**
```typescript
// DailyGem.tsx line 196 replacement
onFeedbackSubmitted={(interpretation) => {
  setShowFeedbackModal(true);
  if (interpretation?.overall_sentiment === 'positive') {
    setAiSyncedFeedback('LIKE');
  } else if (interpretation?.overall_sentiment === 'negative') {
    setAiSyncedFeedback('DISLIKE');
  }
  // neutral / null / missing: do not change toggle
}}
```

Note: `AIFeedbackInput.tsx` already calls `onFeedbackSubmitted?.(response.interpretation)` at line 88 — the **caller** already passes the object. Only the **receiver** in `DailyGem.tsx` needs updating. [VERIFIED: direct file inspection]

### Pitfall 2: ImprovementStory fetchMetrics Closure Stale State

**What goes wrong:** If `fetchMetrics` is defined inside a `useEffect` and then referenced from the event listener effect, it will capture a stale closure.
**Why it happens:** `useEffect` with empty deps captures state at mount time.
**How to avoid:** Define `fetchMetrics` as a `useCallback` or as a plain function at component scope (not inside a `useEffect`). The component's current implementation is already structured with inline `.then()` chains — lift that into a named function at the top of the component body, before the `useEffect` calls.

### Pitfall 3: MetricsStrip fetchMetrics Signature Leftover

**What goes wrong:** After removing the "Refresh stats" button per UI-01, the `fetchMetrics` function still has the `showRefreshing = false` parameter and `setRefreshing(true)` internal call. If not cleaned up, TypeScript will flag unused state variables and the optional parameter creates dead code.
**Why it happens:** The button removal is obvious but the state variables (`refreshing`, `setRefreshing` on lines 32, 36, 45) are easily overlooked.
**How to avoid:** Remove all three: the state declaration on line 32, the `setRefreshing(true)` call on line 36, the `setRefreshing(false)` call on line 45, and simplify `fetchMetrics` to `async () => void`.

### Pitfall 4: getPopularityLabel Used in Two Places in TopArtists.tsx

**What goes wrong:** `getPopularityColor` is called twice in `TopArtists.tsx` — once for the `TrendingUp` icon className (line 158) and once for the popularity text (line 174). If the planner only replaces one usage, the icon and text will be inconsistent.
**Why it happens:** The icon badge and the text label are in different JSX subtrees.
**How to avoid:** Replace `getPopularityColor` entirely with `getPopularityLabel`. Call it once per artist, destructure `{ label, color }`, use `color` for the icon className AND the text className, and use `label` for the text content.

**Updated JSX pattern:**
```tsx
// Call once per artist card render
const pop = getPopularityLabel(artist.popularity);

// Icon badge (line ~158):
<TrendingUp className={`w-3 h-3 ${pop.color}`} />

// Text label (line ~174):
<div className={`text-xs mt-1 ${pop.color}`}>
  {pop.label}
</div>
```

---

## Code Examples

### SYNC-01: Updated _build_prompt schema block (Python)

```python
# Source: direct inspection of backend/apps/ai/ai_feedback_service.py
# Add overall_sentiment as the second-to-last field, before confidence:

"""
    "familiarity_context": "already_heard" | "new_discovery" | null,
    "time_context": "morning" | "afternoon" | "evening" | "night" | null,
    "activity_context": "workout" | "relaxation" | "party" | "focus" | "driving" | null,
    "overall_sentiment": "positive" | "negative" | "neutral" | null,
    "confidence": 0.0-1.0
"""
```

### SYNC-03: aiSyncedFeedback state in DailyGem.tsx

```typescript
// Add alongside existing state declarations:
const [aiSyncedFeedback, setAiSyncedFeedback] = useState<'LIKE' | 'DISLIKE' | null>(null);

// FeedbackButtonGroup JSX addition:
<FeedbackButtonGroup
  trackId={track.id}
  onDislike={() => setShowNewGemPrompt(true)}
  syncedFeedback={aiSyncedFeedback}   // NEW
/>
```

### UI-02: New getPopularityLabel function for TopArtists.tsx

```typescript
// Source: direct inspection of TopArtists.tsx — replace getPopularityColor entirely

const getPopularityLabel = (popularity: number): { label: string; color: string } => {
  if (popularity < 40) return { label: 'Hidden Gem', color: 'text-green' };
  if (popularity < 70) return { label: 'Rising', color: 'text-yellow-400' };
  return { label: 'Mainstream', color: 'text-gray-400' };
};
```

Note: `text-green` is the project's custom Tailwind alias for `#1DB954` (Spotify green), confirmed in `tailwind.config.ts` line 23. `text-yellow-400` and `text-gray-400` are stock Tailwind v3 classes — no config changes needed. [VERIFIED: direct file inspection]

---

## State of the Art

No library upgrades or paradigm shifts apply to this phase. All patterns are standard React 18 / Next.js 14 App Router patterns already established in the codebase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `syncedFeedback` null guard in SYNC-02 `useEffect` should use `!= null` not `!== null` to also guard against undefined | Architecture Patterns — Pattern 1 | Low: both `!= null` and `!== null` work here since the prop is typed; TypeScript would catch undefined |
| A2 | Adding `overall_sentiment` between `activity_context` and `confidence` in `_build_prompt` is the cleanest insertion point | Code Examples — SYNC-01 | Low: field order in JSON schema does not affect OpenAI parsing |
| A3 | Keyword matching rules for `overall_sentiment` in `_fallback_interpretation` suggested above cover common cases | Architecture Patterns — Pattern 3 | Low: fallback path is used only when OpenAI is unavailable; imperfect matching still produces a non-crashing null |

**All critical findings were verified by direct file inspection. No external documentation was required.**

---

## Open Questions (RESOLVED)

1. **Should `aiSyncedFeedback` reset to `null` when a new gem loads?**
   - What we know: `DailyGem.tsx` calls `fetchGem(true)` which replaces `gem` state. `FeedbackButtonGroup` resets `selectedFeedback` to `null` in its own `useEffect` when `trackId` changes (line 52).
   - What's unclear: If `aiSyncedFeedback` holds a stale `'LIKE'` from the previous gem, the `syncedFeedback` prop will re-sync the new gem's toggle immediately.
   - Recommendation: Reset `aiSyncedFeedback` to `null` inside `fetchGem` before the `get()` call (or alongside `setGem(data)`). This mirrors how `selectedFeedback` in `FeedbackButtonGroup` resets on trackId change. Not a blocker but should be explicit in the plan.
   - **RESOLVED: D-01 — reset aiSyncedFeedback to null before fetchGem get() call.**

2. **Should EVOLVE-01 dispatch also fire on the initial mount load?**
   - What we know: EVOLVE-01 says "fires on both initial load and force_new regeneration." `ImprovementStory` already fetches on mount independently. If the initial `fetchGem()` also dispatches, `ImprovementStory` will double-fetch on page load.
   - What's unclear: Whether the double-fetch is acceptable (both calls are cheap, idempotent GET requests) or whether the event should only fire on `force_new = true`.
   - Recommendation: Fire on both as specified by EVOLVE-01. The double-fetch on initial load is harmless (the second fetch just overwrites with identical data). Simplicity > optimization here.
   - **RESOLVED: D-02 — dispatch fires on every fetchGem call, not on mount.**

---

## Environment Availability

> SKIPPED — this phase is code/config-only changes. No external dependencies, no new CLIs, no database changes, no new services.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend only — no frontend test framework configured) |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_ai_feedback_service.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SYNC-01 | `_build_prompt` includes `overall_sentiment` field in schema string | unit | `cd backend && python -m pytest tests/test_ai_feedback_service.py -x -k "overall_sentiment"` | ❌ Wave 0 — new test needed |
| SYNC-01 | `_fallback_interpretation` returns `overall_sentiment` key (even if None) | unit | `cd backend && python -m pytest tests/test_ai_feedback_service.py -x -k "fallback"` | partial — existing fallback test at line 100 needs extension |
| SYNC-02 | `FeedbackButtonGroup` visual toggle syncs from prop without API call | manual-only | — | No frontend test framework |
| SYNC-03 | `DailyGem.tsx` wires `overall_sentiment` to `aiSyncedFeedback` | manual-only | — | No frontend test framework |
| EVOLVE-01 | `fetchGem` dispatches `songscope:new-gem` CustomEvent | manual-only | — | No frontend test framework |
| EVOLVE-02 | `ImprovementStory` refetches on `songscope:new-gem` event | manual-only | — | No frontend test framework |
| UI-01 | MetricsStrip renders without "Refresh stats" button | manual-only | — | No frontend test framework |
| UI-02 | `getPopularityLabel` returns correct tiers | unit | `cd backend && python -m pytest` (no Python equivalent — frontend only) | No frontend test framework |
| UI-03 | Expanded row uses `bg-gray-800` not `bg-gray-850` | manual-only (visual) | — | No frontend test framework |
| UI-04 | Section subtitle reads "Your genre taste profile" | manual-only (visual) | — | No frontend test framework |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_ai_feedback_service.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Full backend suite green before `/gsd:verify-work`. Frontend changes verified via manual smoke-test checklist.

### Wave 0 Gaps
- [ ] `backend/tests/test_ai_feedback_service.py` — extend `test_interpret_feedback_fallback` to assert `"overall_sentiment"` key present in fallback output
- [ ] `backend/tests/test_ai_feedback_service.py` — add `test_build_prompt_contains_overall_sentiment` asserting `"overall_sentiment"` appears in `_build_prompt` output string

*(All other gaps are frontend-only and require no Wave 0 setup given no frontend test framework is configured.)*

---

## Security Domain

Phase 10 has no new API endpoints, no new authentication paths, no data persistence changes, and no new user-controlled inputs beyond what already exists. The `overall_sentiment` field is an OpenAI output read by the frontend — it does not alter the backend storage or query surface.

ASVS V5 (Input Validation): The `overall_sentiment` value from OpenAI is mapped by the frontend via an `=== 'positive'` / `=== 'negative'` equality check before being used to set UI state. Unknown or malformed values fall through to `null` (no-op). This is safe by construction.

No security work required for this phase.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection: `frontend/app/profile/components/DailyGem/DailyGem.tsx` — component structure, existing state, onFeedbackSubmitted call site
- Direct inspection: `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx` — internal state management, prop interface
- Direct inspection: `frontend/app/profile/components/Feedback/AIFeedbackInput.tsx` — onFeedbackSubmitted call signature (passes interpretation object)
- Direct inspection: `frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx` — current fetch pattern, "use client" confirmed
- Direct inspection: `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` — Refresh stats button lines 89-95, state lines 32/36/45
- Direct inspection: `frontend/app/profile/components/TopArtists/TopArtists.tsx` — `getPopularityColor` dual usage lines 158/174, `bg-gray-850` line 190
- Direct inspection: `frontend/app/profile/page.tsx` — section labels lines 79/83
- Direct inspection: `backend/apps/ai/ai_feedback_service.py` — `_build_prompt` schema, `_fallback_interpretation` dict
- Direct inspection: `frontend/tailwind.config.ts` — confirmed `green: "#1DB954"` custom alias, no gray-850 or gray-750 in config

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md — exact requirement text for all 9 IDs
- ROADMAP.md — Phase 10 success criteria

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; confirmed by package.json/requirements inspection
- Architecture: HIGH — all decisions based on direct codebase reading, not inference
- Pitfalls: HIGH — derived from actual file contents (exact line numbers cited)

**Research date:** 2026-06-19
**Valid until:** 2026-07-19 (stable codebase; no fast-moving dependencies)
