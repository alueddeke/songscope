# Phase 8: Frontend Score Breakdown - Pattern Map

**Mapped:** 2026-05-19
**Files analyzed:** 3 (1 new, 2 modified)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx` | component | transform | `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx` | role-match (sub-component extraction pattern) |
| `frontend/app/profile/components/DailyGem/DailyGem.tsx` | component | request-response | itself (modification) | exact — add interface field, import, destructure, JSX insertion |
| `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` | component | request-response | itself (modification) | exact — add interface field, swap one Stat call |

---

## Pattern Assignments

### `frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx` (component, transform)

**Analog:** `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx`

**Sub-component file structure pattern** (lines 1-11):
```typescript
'use client'

import {
  FeedbackType,
  FeedbackButton,
  SelectableFeedbackType,
} from "./FeedbackButton";
import { useCallback, useEffect, useState } from "react";

interface FeedbackButtonGroupProps {
  trackId: string;
  onTrackRemoved?: () => void;
}
```
Key conventions: `'use client'` at top, props interface directly above the function, single default export. `ScoreBreakdown.tsx` follows this exactly — no imports needed beyond the `"use client"` directive since the component is pure render (no hooks, no API calls).

**Core render pattern — display helper with early return** (analog: `DailyGem.tsx` lines 28-32, `MetricsStrip.tsx` `Stat` lines 19-26):
```typescript
// Pure display helper — no state, early return on empty input
function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 min-w-[100px]">
      <span className="text-green text-lg font-bold tabular-nums">{value}</span>
      <span className="text-gray-500 text-xs uppercase tracking-widest">{label}</span>
    </div>
  );
}
```
`ScoreBreakdown` is this same pattern at component scale: pure display, no state, returns `null` on empty input.

**Tailwind color and track pattern** (from `DailyGem.tsx` loading dots, lines 65-66):
```typescript
className="w-2 h-2 rounded-full bg-green animate-bounce"
```
`bg-green` is the established Spotify-green token; `rounded-full` is used consistently for circular/pill shapes; `bg-gray-800` is the established subtle container background (used at `DailyGem.tsx` line 181: `border-gray-800`, `MetricsStrip.tsx` line 62: `border-gray-800`).

**Full ScoreBreakdown component to create:**
```typescript
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

---

### `frontend/app/profile/components/DailyGem/DailyGem.tsx` (component, request-response — modification)

**Analog:** itself — four additive changes to existing code.

**Imports block** (lines 1-9 — current state):
```typescript
"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { get } from "../../../../services/axios";
import FeedbackButtonGroup from "../Feedback/FeedbackButtonGroup";
import AIFeedbackInput from "../Feedback/AIFeedbackInput";
import { AddToLiked } from "../AddToLiked/AddToLiked";
import { AudioPlayer } from "../AudioPlayer/AudioPlayer";
```
Add one line after the `FeedbackButtonGroup` import:
```typescript
import ScoreBreakdown from "./ScoreBreakdown";
```

**Interface to update** (lines 21-26 — current state):
```typescript
interface DailyGemResponse {
  track: GemTrack;
  explanation: string;
  date: string;
  cached: boolean;
}
```
Add `score_breakdown` field:
```typescript
interface DailyGemResponse {
  track: GemTrack;
  explanation: string;
  score_breakdown: Record<string, number>;  // ADD — from Phase 7 API
  date: string;
  cached: boolean;
}
```

**Destructure site** (line 91 — current state):
```typescript
const { track, explanation, date } = gem;
```
Add `score_breakdown` to the existing destructure (same line, after null guard at line 75):
```typescript
const { track, explanation, date, score_breakdown } = gem;
```

**JSX insertion point** (lines 150-162 — conditional rendering pattern):
```typescript
{/* AI explanation — only render when non-empty to avoid orphan border */}
{explanation && (
  <blockquote className="border-l-2 border-green pl-4 py-1">
    <p className="text-gray-300 italic text-sm leading-relaxed">{explanation}</p>
  </blockquote>
)}

{/* Audio preview */}
{track.preview_url && (
  <div className="flex flex-col gap-1">
    <span className="text-gray-500 text-xs uppercase tracking-wider">Preview</span>
    <AudioPlayer src={track.preview_url} />
  </div>
)}
```
Insert `<ScoreBreakdown>` between the blockquote and the audio preview (after line 154, before line 156):
```typescript
{/* Score breakdown bars — renders null internally when score_breakdown is empty */}
<ScoreBreakdown breakdown={score_breakdown ?? {}} />
```

---

### `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` (component, request-response — modification)

**Analog:** itself — three changes: interface field, derivation variable, one JSX swap.

**Interface** (lines 6-17 — current state):
```typescript
interface Metrics {
  total_recommended: number;
  avg_popularity: number;
  novel_track_rate: number;
  hidden_gem_rate: number;
  gem_total: number;
  gem_liked: number;
  gem_disliked: number;
  gem_acceptance_rate: number | null;
  top_genres: string[];
  message?: string;
}
```
Add `compound_hit_rate`; leave `gem_acceptance_rate` for type safety (D-11):
```typescript
interface Metrics {
  total_recommended: number;
  avg_popularity: number;
  novel_track_rate: number;
  hidden_gem_rate: number;
  gem_total: number;
  gem_liked: number;
  gem_disliked: number;
  gem_acceptance_rate: number | null;  // keep — type safety only, not displayed
  compound_hit_rate: number | null;    // ADD — from Phase 7 API
  top_genres: string[];
  message?: string;
}
```

**Derivation variable pattern** (lines 56-59 — existing `acceptance` variable):
```typescript
const acceptance =
  metrics.gem_acceptance_rate !== null
    ? `${Math.round(metrics.gem_acceptance_rate * 100)}%`
    : "—";
```
Add a parallel `hitRate` derivation (use `!= null` to also catch `undefined` on pre-Phase-7 cached responses):
```typescript
const hitRate =
  metrics.compound_hit_rate != null
    ? `${Math.round(metrics.compound_hit_rate * 100)}%`
    : "—";
```

**Stat component pattern** (lines 19-26, used at lines 65-69):
```typescript
function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 min-w-[100px]">
      <span className="text-green text-lg font-bold tabular-nums">{value}</span>
      <span className="text-gray-500 text-xs uppercase tracking-widest">{label}</span>
    </div>
  );
}
```

**JSX swap** (line 67 — current state):
```typescript
<Stat label="Acceptance rate" value={acceptance} />
```
Replace with (D-07, D-08, D-09):
```typescript
<Stat label="Hit rate" value={hitRate} />
```
The `acceptance` variable and its derivation can be removed once `hitRate` is added, since `gem_acceptance_rate` is no longer displayed.

---

## Shared Patterns

### `"use client"` Directive
**Source:** `DailyGem.tsx` line 1, `MetricsStrip.tsx` line 1, `FeedbackButtonGroup.tsx` line 1
**Apply to:** `ScoreBreakdown.tsx` (new file) — all components in this directory are client components
```typescript
"use client";
```

### Conditional Rendering Guard
**Source:** `DailyGem.tsx` lines 150-154
**Apply to:** `DailyGem.tsx` JSX insertion — same `{condition && (...)}` idiom used for explanation blockquote; `ScoreBreakdown` returns `null` internally so its guard is inside the component, not at the call site
```typescript
{explanation && (
  <blockquote className="border-l-2 border-green pl-4 py-1">
    <p className="text-gray-300 italic text-sm leading-relaxed">{explanation}</p>
  </blockquote>
)}
```

### Null-safe Metric Derivation
**Source:** `MetricsStrip.tsx` lines 56-59
**Apply to:** `MetricsStrip.tsx` — `hitRate` derivation follows exact same ternary structure as existing `acceptance`; use `!= null` (double-equals) instead of `!== null` to guard against `undefined` on pre-Phase-7 cached responses
```typescript
const acceptance =
  metrics.gem_acceptance_rate !== null
    ? `${Math.round(metrics.gem_acceptance_rate * 100)}%`
    : "—";
```

### Tailwind Color Tokens
**Source:** `tailwind.config.ts` (confirmed); used throughout `DailyGem.tsx` and `MetricsStrip.tsx`
**Apply to:** `ScoreBreakdown.tsx` bar fill
- `bg-green` — Spotify green (#1DB954), the single accent color
- `bg-gray-800` — subtle container/track background
- `text-gray-300` — secondary text (labels, values)
- `text-gray-500` — muted text (used in MetricsStrip stat labels)
- `rounded-full` — pill/circle shape for bars and badges

---

## No Analog Found

No files in this phase lack a codebase analog. All three files have direct patterns in the existing component tree.

---

## Metadata

**Analog search scope:** `frontend/app/profile/components/` (DailyGem, MetricsStrip, Feedback subdirectories)
**Files scanned:** 4 (DailyGem.tsx, MetricsStrip.tsx, FeedbackButtonGroup.tsx — read in full; directory listing for orientation)
**Pattern extraction date:** 2026-05-19

**Key notes for planner:**
- `DailyGem.tsx` line 91 is the destructure site — `score_breakdown` must be added here, after the `if (!gem)` null guard at line 75
- `MetricsStrip.tsx` line 67 is the exact Stat swap target — `<Stat label="Acceptance rate" value={acceptance} />` becomes `<Stat label="Hit rate" value={hitRate} />`
- Pre-existing TypeScript build error in `TopArtists.tsx:85` is unrelated to this phase — do not attribute to phase work
- No new npm packages are required; no new API calls are added
