---
phase: 08-frontend-score-breakdown
reviewed: 2026-05-19T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx
  - frontend/app/profile/components/DailyGem/DailyGem.tsx
  - frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx
findings:
  critical: 2
  warning: 5
  info: 2
  total: 9
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-05-19T00:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three components were reviewed: `ScoreBreakdown` (new), `DailyGem` (modified to wire in score breakdown), and `MetricsStrip` (modified). The score breakdown rendering contains a critical overflow bug — values for `feedback_multiplier` are expected to exceed 1.0 but the percentage formula has no clamp, causing bar overflow. A second critical issue exists in `DailyGem` where copy rendered to all users with popularity ≥ 40 falsely asserts tracks are obscure. There are five warnings covering silent error suppression, nullable field inconsistency, and a debug UI button exposed in production.

---

## Critical Issues

### CR-01: Score bar width overflows 100% for `feedback_multiplier` — visual corruption and data misrepresentation

**File:** `frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx:20`

**Issue:** The percentage formula `Math.round(raw * 100 / 5) * 5` assumes `raw` is in the range [0, 1]. However `feedback_multiplier` is a score multiplier that commonly exceeds 1.0 (e.g. 1.2×, 1.5×). A value of 1.2 yields `pct = 120`, and the rendered div gets `style={{ width: "120%" }}`. The parent has `overflow-hidden` but that only clips the visual; the bar silently reads as "full" while the label shows `120%`, which is confusing and wrong. Negative values (valid for novelty penalty) similarly produce `width: "-X%"` which renders as zero with a misleading label.

**Fix:** Clamp `pct` to [0, 100] after computing it. Also remove the step-rounding to 5% multiples unless that is intentional design — it discards precision without surfacing that loss to the user.

```tsx
// ScoreBreakdown.tsx line 20
const raw = breakdown[key] ?? 0;
// Convert from whatever raw scale backend uses; clamp to valid CSS range.
const pct = Math.min(100, Math.max(0, Math.round(raw * 100)));
```

If `feedback_multiplier` uses a different scale (e.g. 0.5–2.0 representing 50%–200%), normalize it explicitly before clamping:

```tsx
const SCALE: Record<string, number> = {
  feedback_multiplier: 2.0, // max expected value of the multiplier
};
const scale = SCALE[key] ?? 1.0;
const pct = Math.min(100, Math.max(0, Math.round((raw / scale) * 100)));
```

---

### CR-02: Hardcoded copy "most listeners have never heard this" is shown for tracks with popularity up to 100

**File:** `frontend/app/profile/components/DailyGem/DailyGem.tsx:147`

**Issue:** The inline description `"most listeners have never heard this"` is rendered unconditionally alongside the popularity badge, regardless of the track's actual popularity score. The `popularityLabel` function caps its output at `"Under the radar"` for any score ≥ 40 (line 33), meaning a track with popularity 85 or 95 gets the label "Under the radar" with the tooltip "most listeners have never heard this." This is factually wrong and can mislead users about a track they likely do know.

**Fix:** Remove or gate the static copy. Render it only for the genuinely rare tiers, or replace with a dynamic description derived from the label:

```tsx
const POP_DESCRIPTIONS: Record<string, string> = {
  "Ultra rare":       "almost no one has heard this",
  "Hidden gem":       "most listeners have never heard this",
  "Under the radar":  "below mainstream popularity",
};

// In JSX:
<span className="text-gray-400 text-xs">
  ♦ {pop.label} · {POP_DESCRIPTIONS[pop.label]} ({track.popularity}/100)
</span>
```

---

## Warnings

### WR-01: `MetricsStrip` swallows fetch errors with no logging

**File:** `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx:41-43`

**Issue:** The `catch {}` block silently sets `fetchFailed = true` but discards the error object entirely. When the metrics endpoint fails (network error, 401, 500), there is no observable log for debugging — in contrast to `DailyGem` which correctly logs via `console.error`. Silent failure makes production incident diagnosis needlessly hard.

**Fix:**
```tsx
} catch (err) {
  console.error("MetricsStrip fetch error:", err);
  setFetchFailed(true);
}
```

---

### WR-02: `hidden_gem_rate` treated as non-nullable but may be null/undefined from the API

**File:** `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx:70`

**Issue:** The `Metrics` interface declares `hidden_gem_rate: number` (non-nullable), while the structurally similar fields `gem_acceptance_rate` and `compound_hit_rate` are declared `number | null` (lines 14-15). The rendering code calls `Math.round(metrics.hidden_gem_rate * 100)` with no null guard. If the backend returns `null` for this field (consistent with how it returns null for the others when data is absent), this produces `NaN%` rendered to the user, or `0%` if `Math.round(null * 100)` coerces — both are silently wrong.

**Fix:** Align the interface and handle the null case:
```tsx
// In Metrics interface:
hidden_gem_rate: number | null;

// In render:
<Stat
  label="Hidden gem rate"
  value={
    metrics.hidden_gem_rate != null
      ? `${Math.round(metrics.hidden_gem_rate * 100)}%`
      : "—"
  }
/>
```

---

### WR-03: `date` string timezone handling changes semantics across locales

**File:** `frontend/app/profile/components/DailyGem/DailyGem.tsx:95`

**Issue:** `new Date(date + "T00:00:00")` appends a local-time suffix to a YYYY-MM-DD string. Per the ECMAScript spec, bare `YYYY-MM-DD` strings are parsed as UTC midnight. Adding `T00:00:00` without a `Z` suffix switches the parse to *local* midnight. For users in UTC+5 to UTC+12, the resulting date display is one day ahead of the UTC date sent by the server. For users in UTC-1 to UTC-12, the results differ by hours but can still display the wrong calendar date depending on DST.

**Fix:** Use UTC explicitly to match the server's intent:
```tsx
// Append Z to force UTC parse, matching bare YYYY-MM-DD behaviour
const formattedDate = new Date(date + "T00:00:00Z").toLocaleDateString("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric",
  timeZone: "UTC",
});
```

---

### WR-04: `avg_popularity` rendered as a raw float without rounding

**File:** `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx:69`

**Issue:** `avg_popularity` is declared as `number` and rendered directly as `${metrics.avg_popularity}/100`. If the backend returns a float (e.g. `42.857`), the displayed label becomes `42.857/100`, which is unpolished and potentially confusing next to the integer-like stat.

**Fix:**
```tsx
<Stat label="Avg popularity" value={`${Math.round(metrics.avg_popularity)}/100`} />
```

---

### WR-05: Production UI exposes a testing/debug control with no environment guard

**File:** `frontend/app/profile/components/DailyGem/DailyGem.tsx:191-199`

**Issue:** The "Generate new gem" button is annotated in the source comment as `Testing mode — generate a new gem without waiting until tomorrow`. It is rendered unconditionally for all users in production. Each click calls `/api/daily-gem/?force_new=true`, bypassing the cache and triggering a full ML scoring pipeline. Beyond the UX concern (users could spam-generate and exhaust rate limits or backend resources), it is explicitly a development affordance that was not gated.

**Fix:** Guard behind a development environment check or remove before ship:
```tsx
{process.env.NODE_ENV === "development" && (
  <div className="pt-2 border-t border-gray-800">
    <button
      onClick={() => fetchGem(true)}
      className="text-gray-500 text-xs hover:text-gray-300 transition-colors"
    >
      [DEV] Generate new gem
    </button>
  </div>
)}
```

---

## Info

### IN-01: Spotify logo uses `<img>` instead of Next.js `<Image>`

**File:** `frontend/app/profile/components/DailyGem/DailyGem.tsx:178`

**Issue:** The Spotify logo is rendered with a bare `<img>` tag while the rest of the component uses Next.js `<Image>` for optimized delivery. This is inconsistent and misses automatic lazy-loading and format optimization for the asset.

**Fix:**
```tsx
import Image from "next/image";

// In JSX:
<Image src="/images/spotify-logo.png" alt="Spotify" width={16} height={16} />
```

---

### IN-02: `ScoreBreakdown` renders nothing for unknown keys — missing keys are silently dropped

**File:** `frontend/app/profile/components/DailyGem/ScoreBreakdown.tsx:18-29`

**Issue:** `SCORE_ROWS` is a hardcoded static list. If the backend adds a new score component (e.g. `audio_feature_sim`) it will never appear in the breakdown UI, and if the backend renames an existing key, the corresponding row silently shows `0` (via the `?? 0` fallback). There is no warning or indicator that a key was expected but missing.

**Fix:** This is acceptable as intentional design (explicit UI mapping), but worth noting: consider validating that expected keys are present in `breakdown` at render time to catch backend contract drift early, especially during development. A development-only assertion would be sufficient:

```tsx
if (process.env.NODE_ENV === "development") {
  SCORE_ROWS.forEach(({ key }) => {
    if (!(key in breakdown)) {
      console.warn(`ScoreBreakdown: expected key "${key}" not found in breakdown`);
    }
  });
}
```

---

_Reviewed: 2026-05-19T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
