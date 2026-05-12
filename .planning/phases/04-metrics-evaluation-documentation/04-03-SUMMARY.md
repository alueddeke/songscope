---
phase: 04-metrics-evaluation-documentation
plan: "03"
subsystem: frontend-ui
tags: [frontend, react, nextjs, recharts, profile-page, wiring, wave-2]
dependency_graph:
  requires:
    - 04-01 (recharts installed)
    - 04-02 (backend metrics endpoints)
  provides:
    - LikeTrendChart — 7-day rolling like-rate Recharts line chart
    - TasteProfileChart — top-10 genre horizontal Recharts bar chart
    - ImprovementStory — first-7 vs last-7 like-rate stat comparison block
    - DiversityScore — single Jaccard-derived diversity percentage tile
    - profile/page.tsx wired with MetricsStrip and all four new components
  affects:
    - frontend/app/profile/components/LikeTrendChart/LikeTrendChart.tsx
    - frontend/app/profile/components/TasteProfileChart/TasteProfileChart.tsx
    - frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx
    - frontend/app/profile/components/DiversityScore/DiversityScore.tsx
    - frontend/app/profile/page.tsx
tech_stack:
  added: []
  patterns:
    - "use client" directive on all chart/tile components; profile/page.tsx stays server component
    - Self-fetching components (useState + useEffect + silent catch) per MetricsStrip convention
    - Recharts 3.x tooltip formatter typed as (v) => v != null ? string : "" (ValueType compatibility)
    - recharts 3.x BarChart radius prop as [topLeft, topRight, bottomRight, bottomLeft] array
key_files:
  created:
    - frontend/app/profile/components/LikeTrendChart/LikeTrendChart.tsx
    - frontend/app/profile/components/TasteProfileChart/TasteProfileChart.tsx
    - frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx
    - frontend/app/profile/components/DiversityScore/DiversityScore.tsx
  modified:
    - frontend/app/profile/page.tsx
decisions:
  - "Tooltip formatter typed as (v) => v != null ? string : '' to satisfy recharts 3.x ValueType | undefined signature"
  - "tickFormatter parameter typed as (d: string) to satisfy strict TypeScript — recharts XAxis passes string when dataKey is a string field"
  - "npm install run to install recharts node_modules (package.json had recharts@^3.8.1 but node_modules was absent — Rule 3 auto-fix)"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-12"
  tasks_completed: 3
  tasks_total: 4
  files_changed: 5
---

# Phase 4 Plan 03: Frontend Metrics Dashboard (Wave 2) Summary

Four new "use client" chart and stat-tile components built with Recharts and wired into profile/page.tsx alongside the previously-unwired MetricsStrip, delivering a complete metrics dashboard below the TopArtists section on /profile.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Build LikeTrendChart + TasteProfileChart | c5f5e543 | frontend/app/profile/components/LikeTrendChart/LikeTrendChart.tsx, frontend/app/profile/components/TasteProfileChart/TasteProfileChart.tsx |
| 2 | Build ImprovementStory + DiversityScore | e345cd48 | frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx, frontend/app/profile/components/DiversityScore/DiversityScore.tsx |
| 3 | Wire MetricsStrip + four new components into profile/page.tsx | 71cf7872 | frontend/app/profile/page.tsx |
| 4 | Human verification of metrics dashboard at /profile | — | Awaiting user checkpoint |

## What Was Built

### Task 1: LikeTrendChart (88 lines)

File: `frontend/app/profile/components/LikeTrendChart/LikeTrendChart.tsx`

- Fetches `GET /api/recommendation-trend/` — returns `TrendPoint[]`
- Renders Recharts `<LineChart>` inside `<ResponsiveContainer width="100%" height={220}>`
- Line: `stroke="#1DB954"`, `strokeWidth={2}`, `dot={false}`, `type="monotone"`
- X-axis: `tickFormatter` formats ISO date to `"MMM D"` locale string
- Y-axis: `domain={[0, 100]}`
- Tooltip: dark card (`#111827` background, `#374151` border)
- Cold-start (<2 data points): "Not enough data yet — your like-rate trend will appear after a few days of gems."
- Loading: 3-dot bouncing pattern (no text, matching MetricsStrip silent pattern)

### Task 1: TasteProfileChart (80 lines)

File: `frontend/app/profile/components/TasteProfileChart/TasteProfileChart.tsx`

- Fetches `GET /api/recommendation-metrics/` and reads `top_genres_pct`
- Renders Recharts horizontal `<BarChart layout="vertical">` inside `<ResponsiveContainer width="100%" height={280}>`
- Bar: `fill="#1DB954"`, `radius={[0, 3, 3, 0]}`
- Y-axis: `type="category" dataKey="genre" width={120}`, tick fill `#9ca3af`
- X-axis: `type="number" domain={[0, 100]}`, tick fill `#6b7280`
- Cold-start (empty array): "Your taste profile will appear once your listening history builds up."

### Task 2: ImprovementStory (60 lines)

File: `frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx`

- Fetches `GET /api/recommendation-metrics/` and reads `improvement_story`
- Returns `null` when `loading || !story || first_7_rate === null || last_7_rate === null` (cold-start skip)
- Renders two `Stat` sub-components: "When I started" + "Now" (matching MetricsStrip Stat pattern exactly)
- Delta badge: `▲ +{N}pp` in `text-green text-xs`, `▼ {N}pp` in `text-red-400 text-xs`, `— 0pp` in `text-gray-500 text-xs`

### Task 2: DiversityScore (38 lines)

File: `frontend/app/profile/components/DiversityScore/DiversityScore.tsx`

- Fetches `GET /api/recommendation-metrics/` and reads `diversity_score`
- Returns `null` when loading (silent, no bouncing dots — tile pattern)
- Displays `(score * 100).toFixed(0)%` when score is a number, `"—"` when null
- Label "Genre diversity" with `text-xs text-gray-500 uppercase tracking-widest`
- Native browser tooltip via `title` attribute on wrapping `<div>`

### Task 3: profile/page.tsx additions

Exact JSX additions to `frontend/app/profile/page.tsx`:

**New imports (lines 6–10):**
```tsx
import MetricsStrip from './components/MetricsStrip/MetricsStrip'
import LikeTrendChart from './components/LikeTrendChart/LikeTrendChart'
import TasteProfileChart from './components/TasteProfileChart/TasteProfileChart'
import DiversityScore from './components/DiversityScore/DiversityScore'
import ImprovementStory from './components/ImprovementStory/ImprovementStory'
```

**New JSX block (after TopArtists section):**
```tsx
<MetricsStrip />

<section className="w-full border-t border-gray-800 py-16 px-4 md:px-8 lg:px-16">
  <h2 className="text-2xl font-bold text-white mb-8">How your taste is evolving</h2>
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
    <div>
      <p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Like-rate trend (7-day rolling)</p>
      <LikeTrendChart />
    </div>
    <div>
      <p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Your taste profile</p>
      <TasteProfileChart />
    </div>
  </div>
  <div className="flex flex-wrap gap-8 mt-12 pt-8 border-t border-gray-800">
    <DiversityScore />
    <ImprovementStory />
  </div>
</section>
```

profile/page.tsx remains a server component (no `"use client"`, no React hooks added).

## Deviations from Plan

### Auto-fix 1: [Rule 3 - Blocking] npm install required for recharts

**Found during:** Task 1
**Issue:** `recharts@^3.8.1` was in `package.json` (added in 04-01) but `node_modules/recharts` was absent in the worktree — `npx tsc --noEmit` reported `Cannot find module 'recharts'`.
**Fix:** Ran `npm install` to populate `node_modules`. No version change — npm resolved `recharts@3.8.1` as before.
**Files modified:** `frontend/package-lock.json` (no content change — already reflected 3.8.1)
**Impact:** Unblocked TypeScript compilation for both chart components.

### Auto-fix 2: [Rule 1 - Bug] Recharts 3.x Tooltip formatter type mismatch

**Found during:** Task 1 (TypeScript compilation)
**Issue:** `formatter={(v: number) => \`${v}%\`}` produced `TS2322`: recharts 3.x `Formatter<ValueType, NameType>` passes `ValueType | undefined`, not `number`. Annotating `v` as `number` caused a type incompatibility.
**Fix:** Changed to `formatter={(v) => (v != null ? \`${v}%\` : "")}` — removes the explicit annotation, uses null-guard to satisfy the `undefined` branch, and produces the same visible output.
**Files modified:** LikeTrendChart.tsx, TasteProfileChart.tsx
**Impact:** TypeScript compiles cleanly with no behavior change.

### Auto-fix 3: [Rule 1 - Bug] XAxis tickFormatter implicit any parameter

**Found during:** Task 1 (TypeScript compilation)
**Issue:** `tickFormatter={(d) => new Date(d)...}` reported `TS7006: Parameter 'd' implicitly has an 'any' type` under strict mode.
**Fix:** Added explicit type annotation `(d: string)` — correct for an XAxis whose `dataKey="date"` maps to a string field.
**Files modified:** LikeTrendChart.tsx

## Known Stubs

None. All four components are fully implemented with real API calls and complete render branches (loading, cold-start, data). profile/page.tsx wires all five components.

## Threat Surface Scan

No new network endpoints or auth paths introduced. All five components issue GET requests to existing `/api/recommendation-metrics/` and `/api/recommendation-trend/` — both protected by `IsAuthenticated` per plan 04-02. Genre strings rendered as React text children (JSX auto-escape). No `dangerouslySetInnerHTML` used anywhere. T-04-12 through T-04-17 mitigated as planned.

## Human Verification (Task 4)

Awaiting user approval of the visual checkpoint. User must run backend + frontend dev servers, navigate to `/profile`, and verify all 11 checklist items in the plan's `<how-to-verify>` block.

## Self-Check: PASSED

- `frontend/app/profile/components/LikeTrendChart/LikeTrendChart.tsx` exists (88 lines): FOUND
- `frontend/app/profile/components/TasteProfileChart/TasteProfileChart.tsx` exists (80 lines): FOUND
- `frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx` exists (60 lines): FOUND
- `frontend/app/profile/components/DiversityScore/DiversityScore.tsx` exists (38 lines): FOUND
- `frontend/app/profile/page.tsx` contains "How your taste is evolving": VERIFIED
- All four new files have `"use client"` on line 1: VERIFIED
- `grep -c '"use client"' frontend/app/profile/page.tsx` == 0: VERIFIED
- `cd frontend && npx tsc --noEmit` exits 0: VERIFIED
- Commit c5f5e543 exists: VERIFIED
- Commit e345cd48 exists: VERIFIED
- Commit 71cf7872 exists: VERIFIED
