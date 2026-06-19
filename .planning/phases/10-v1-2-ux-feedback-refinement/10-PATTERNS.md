# Phase 10: v1.2 UX & Feedback Refinement - Pattern Map

**Mapped:** 2026-06-19
**Files analyzed:** 9 (all modified; no new files created in this phase)
**Analogs found:** 9 / 9 (every file IS its own analog — all are edits to existing files)

---

## File Classification

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx` | component | request-response + controlled-prop | Self (existing internal state + useEffect on trackId) | exact |
| `frontend/app/profile/components/DailyGem/DailyGem.tsx` | component | request-response + event-driven | Self (existing fetchGem, useState, useEffect) | exact |
| `frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx` | component | request-response + event-driven | Self (existing get() fetch in useEffect) | exact |
| `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` | component | request-response | Self (existing fetchMetrics + useState) | exact |
| `frontend/app/profile/components/TopArtists/TopArtists.tsx` | component | request-response | Self (existing getPopularityColor utility fn + JSX) | exact |
| `frontend/app/profile/page.tsx` | page (Server Component) | request-response | Self (existing static string in JSX) | exact |
| `backend/apps/ai/ai_feedback_service.py` | service | request-response | Self (_build_prompt schema block, _fallback_interpretation dict) | exact |
| `backend/tests/test_ai_feedback_service.py` | test | — | Self (TestFeedbackInterpreter class, existing test pattern) | exact |

---

## Pattern Assignments

### `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx` (SYNC-02)

**Change:** Add `syncedFeedback?: 'LIKE' | 'DISLIKE' | null` prop to interface; add `useEffect` that mirrors prop into internal state when non-null.

**Existing prop interface** (lines 22–26):
```typescript
interface FeedbackButtonGroupProps {
  trackId: string;
  onTrackRemoved?: () => void;
  onDislike?: () => void;
}
```
Add `syncedFeedback?: 'LIKE' | 'DISLIKE' | null;` as the fourth property. Update function signature destructuring at line 28 to include it.

**Existing useEffect pattern to copy** (lines 51–54) — trackId reset:
```typescript
useEffect(() => {
  setSelectedFeedback(null);
  checkInitialLikeState();
}, [trackId, checkInitialLikeState]);
```
Add a second, parallel `useEffect` immediately after:
```typescript
useEffect(() => {
  if (syncedFeedback != null) {
    setSelectedFeedback(syncedFeedback);
  }
}, [syncedFeedback]);
```
**Critical guard:** `if (syncedFeedback != null)` — do NOT call `setSelectedFeedback` when prop is `null`. That would wipe a user's manual click when the parent resets on new gem load. This is the same intent as the existing null-safe `setSelectedFeedback(null)` inside the trackId effect (that reset is intentional and gated on trackId change, not on syncedFeedback).

**Existing imports** (lines 1–9) — no changes needed:
```typescript
'use client'

import {
  FeedbackType,
  FeedbackButton,
  SelectableFeedbackType,
} from "./FeedbackButton";
import { post, get } from "@/services/axios";
import { useCallback, useEffect, useState } from "react";
```

---

### `frontend/app/profile/components/DailyGem/DailyGem.tsx` (SYNC-03, EVOLVE-01)

**Changes:** (1) Add `aiSyncedFeedback` state. (2) Reset it inside `fetchGem` before `get()`. (3) Wire `onFeedbackSubmitted` callback to read `interpretation.overall_sentiment`. (4) Dispatch CustomEvent after `setGem(data)`. (5) Pass `syncedFeedback` prop to `FeedbackButtonGroup`.

**Existing state block** (lines 37–41) — add new state alongside:
```typescript
const [gem, setGem] = useState<DailyGemResponse | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
const [showNewGemPrompt, setShowNewGemPrompt] = useState(false);
const [showFeedbackModal, setShowFeedbackModal] = useState(false);
```
Add after line 41:
```typescript
const [aiSyncedFeedback, setAiSyncedFeedback] = useState<'LIKE' | 'DISLIKE' | null>(null);
```

**Existing fetchGem function** (lines 43–57):
```typescript
const fetchGem = async (forceNew = false) => {
  try {
    setLoading(true);
    setError(null);
    setShowNewGemPrompt(false);
    const url = forceNew ? "/api/daily-gem/?force_new=true" : "/api/daily-gem/";
    const data = await get<DailyGemResponse>(url);
    setGem(data);
  } catch (err) {
    setError("Could not load today's gem. Try refreshing.");
    console.error("DailyGem fetch error:", err);
  } finally {
    setLoading(false);
  }
};
```
Modify the try block — add reset before `get()` and dispatch after `setGem(data)`:
```typescript
const fetchGem = async (forceNew = false) => {
  try {
    setLoading(true);
    setError(null);
    setShowNewGemPrompt(false);
    setAiSyncedFeedback(null);                                    // D-01: reset before get()
    const url = forceNew ? "/api/daily-gem/?force_new=true" : "/api/daily-gem/";
    const data = await get<DailyGemResponse>(url);
    setGem(data);
    window.dispatchEvent(new CustomEvent('songscope:new-gem'));   // EVOLVE-01
  } catch (err) {
    setError("Could not load today's gem. Try refreshing.");
    console.error("DailyGem fetch error:", err);
  } finally {
    setLoading(false);
  }
};
```

**Existing FeedbackButtonGroup JSX** (lines 186–189):
```tsx
<FeedbackButtonGroup
  trackId={track.id}
  onDislike={() => setShowNewGemPrompt(true)}
/>
```
Add `syncedFeedback` prop:
```tsx
<FeedbackButtonGroup
  trackId={track.id}
  onDislike={() => setShowNewGemPrompt(true)}
  syncedFeedback={aiSyncedFeedback}
/>
```

**Existing onFeedbackSubmitted inline callback** (line 196):
```tsx
onFeedbackSubmitted={() => setShowFeedbackModal(true)}
```
Replace with named handler that reads `interpretation.overall_sentiment`:
```tsx
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
**Note:** `AIFeedbackInput.tsx` line 88 already calls `onFeedbackSubmitted?.(response.interpretation)` — the caller already passes the object. Only the receiver signature changes here.

**Existing imports** (lines 1–10) — no changes needed:
```typescript
"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { get } from "../../../../services/axios";
import FeedbackButtonGroup from "../Feedback/FeedbackButtonGroup";
import ScoreBreakdown from "./ScoreBreakdown";
import AIFeedbackInput from "../Feedback/AIFeedbackInput";
import { AddToLiked } from "../AddToLiked/AddToLiked";
import { AudioPlayer } from "../AudioPlayer/AudioPlayer";
```

---

### `frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx` (EVOLVE-02)

**Change:** Lift the inline fetch chain out of `useEffect` into a named `fetchMetrics` function at component scope; add a second `useEffect` that subscribes to `'songscope:new-gem'` and calls `fetchMetrics()` with cleanup.

**Existing inline useEffect fetch** (lines 30–35):
```typescript
useEffect(() => {
  get<MetricsResponse>("/api/recommendation-metrics/")
    .then((r) => setStory(r.improvement_story ?? null))
    .catch(() => {})
    .finally(() => setLoading(false));
}, []);
```

Refactor to named function at component scope (before any `useEffect` calls), then split into two effects:
```typescript
const fetchMetrics = () => {
  get<MetricsResponse>("/api/recommendation-metrics/")
    .then((r) => setStory(r.improvement_story ?? null))
    .catch(() => {})
    .finally(() => setLoading(false));
};

useEffect(() => {
  fetchMetrics();  // initial load — preserves existing behavior
}, []);

useEffect(() => {
  const handler = () => fetchMetrics();
  window.addEventListener('songscope:new-gem', handler);
  return () => window.removeEventListener('songscope:new-gem', handler);  // mandatory cleanup
}, []);
```
**Cleanup requirement:** `removeEventListener` in the return is mandatory. Without it, each re-mount adds a new listener (memory leak + duplicate fetches).

**Pattern for function placement:** Follow the same component-scope convention established in `MetricsStrip.tsx` lines 35–47 where `fetchMetrics` is defined as a named async function above the `useEffect` block.

**Existing imports** (lines 1–4) — no changes needed:
```typescript
"use client";

import { useState, useEffect } from "react";
import { get } from "../../../../services/axios";
```

---

### `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` (UI-01)

**Change:** Remove the "Refresh stats" button and its supporting state/parameter. Three removal targets, one JSX removal.

**State to remove** (line 32):
```typescript
const [refreshing, setRefreshing] = useState(false);
```
Delete this line entirely.

**fetchMetrics parameter and internal calls to remove** (lines 35–47):
```typescript
const fetchMetrics = async (showRefreshing = false) => {
  if (showRefreshing) setRefreshing(true);   // line 36 — remove this line
  try {
    const data = await get<Metrics>("/api/recommendation-metrics/");
    setMetrics(data);
    setFetchFailed(false);
  } catch {
    setFetchFailed(true);
  } finally {
    setLoading(false);
    setRefreshing(false);   // line 45 — remove this line
  }
};
```
Simplify to:
```typescript
const fetchMetrics = async () => {
  try {
    const data = await get<Metrics>("/api/recommendation-metrics/");
    setMetrics(data);
    setFetchFailed(false);
  } catch {
    setFetchFailed(true);
  } finally {
    setLoading(false);
  }
};
```

**Button JSX to remove** (lines 89–95):
```tsx
<button
  onClick={() => fetchMetrics(true)}
  disabled={refreshing}
  className="text-gray-600 text-xs hover:text-gray-400 transition-colors self-start mt-1"
>
  {refreshing ? "Refreshing…" : "Refresh stats"}
</button>
```
Delete this entire `<button>` block. The surrounding `<div className="flex flex-wrap gap-8 items-start justify-between">` at line 64 can remain or collapse to `<div className="flex flex-wrap gap-8">` if the justify-between is no longer needed without the button — follow the existing layout convention.

---

### `frontend/app/profile/components/TopArtists/TopArtists.tsx` (UI-02, UI-03)

**UI-02 Change:** Replace `getPopularityColor` (returns `string`) with `getPopularityLabel` (returns `{ label: string; color: string }`). Update both JSX call sites.

**Existing function to replace** (lines 38–43):
```typescript
const getPopularityColor = (popularity: number): string => {
  if (popularity >= 80) return 'text-green-400';
  if (popularity >= 60) return 'text-yellow-400';
  if (popularity >= 40) return 'text-orange-400';
  return 'text-red-400';
};
```
Replace entirely with:
```typescript
const getPopularityLabel = (popularity: number): { label: string; color: string } => {
  if (popularity < 40) return { label: 'Hidden Gem', color: 'text-green' };
  if (popularity < 70) return { label: 'Rising', color: 'text-yellow-400' };
  return { label: 'Mainstream', color: 'text-gray-400' };
};
```
Note: `text-green` is the project's custom Tailwind alias for `#1DB954` (confirmed in `tailwind.config.ts` line 23). `text-yellow-400` and `text-gray-400` are standard Tailwind v3 classes. No config changes needed.

**Call site 1 — icon badge** (line 158):
```tsx
<TrendingUp className={`w-3 h-3 ${getPopularityColor(artist.popularity)}`} />
```
This and call site 2 must be replaced together. Add a local const at the top of the artist card render (inside the `artists.forEach` callback, before `gridItems.push(...)`):
```tsx
const pop = getPopularityLabel(artist.popularity);
```
Then replace the icon at line 158:
```tsx
<TrendingUp className={`w-3 h-3 ${pop.color}`} />
```

**Call site 2 — text label** (lines 174–176):
```tsx
<div className={`text-xs mt-1 ${getPopularityColor(artist.popularity)}`}>
  {artist.popularity}% popular
</div>
```
Replace with:
```tsx
<div className={`text-xs mt-1 ${pop.color}`}>
  {pop.label}
</div>
```

**UI-03 Change:** Fix transparent/invisible expanded row background.

**Existing class on expanded row container** (line 190):
```tsx
<div className="bg-gray-850 rounded-lg p-6 border border-gray-700 w-full">
```
`bg-gray-850` is not in the Tailwind config (only `green: #1DB954` is custom; no gray-850 exists — renders as no background). Replace with:
```tsx
<div className="bg-gray-800 rounded-lg p-6 border border-gray-700 w-full">
```

---

### `frontend/app/profile/page.tsx` (UI-04)

**Change:** One string replacement at line 83.

**Existing label** (line 83):
```tsx
<p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Your taste profile</p>
```
Replace string only:
```tsx
<p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Your genre taste profile</p>
```
**Scope:** Line 79 (`"Like-rate trend (7-day rolling)"`) is already correct — do NOT change it. Only line 83 changes.

---

### `backend/apps/ai/ai_feedback_service.py` (SYNC-01)

**Changes:** (1) Add `overall_sentiment` field to JSON schema in `_build_prompt`. (2) Add rule for it. (3) Add `overall_sentiment` key to `_fallback_interpretation` dict with keyword-based assignment.

**Existing schema block** (lines 152–167):
```python
return f"""
Analyze this music feedback and extract structured information:
"{user_text}"{context}

Return a JSON object with these fields (use null if not applicable):
{{
    "tempo_preference": "slower" | "faster" | null,
    ...
    "familiarity_context": "already_heard" | "new_discovery" | null,
    "time_context": "morning" | "afternoon" | "evening" | "night" | null,
    "activity_context": "workout" | "relaxation" | "party" | "focus" | "driving" | null,
    "confidence": 0.0-1.0
}}
```
Insert after `"activity_context"` line (before `"confidence"`):
```python
    "overall_sentiment": "positive" | "negative" | "neutral" | null,
```

**Existing rules block** (lines 170–173):
```python
Rules:
- If user says "this genre" or "this type of music" and Track genres are provided, populate specific_genres from the track genres.
- If user says they already know/have heard the track but still like it, set familiarity_context to "already_heard".
- Only include fields clearly indicated in the feedback. Be conservative - if unsure, use null.
```
Add a third rule before the last line:
```python
- Set overall_sentiment based on the general tone of the feedback: "positive" if the user is satisfied/happy, "negative" if dissatisfied, "neutral" if informational or mixed, null if unclear.
```

**Existing `_fallback_interpretation` dict** (lines 179–194):
```python
interpretation = {
    "tempo_preference": None,
    ...
    "time_context": None,
    "activity_context": None,
    "confidence": 0.3
}
```
Add `"overall_sentiment": None` to the dict (alongside the other `None` keys, before `"confidence"`):
```python
    "overall_sentiment": None,
    "confidence": 0.3
```
Then add keyword matching after the existing `energy_preference` block (after line 211, before `return interpretation`):
```python
if any(word in user_text_lower for word in ["love", "great", "amazing", "good", "like"]):
    interpretation["overall_sentiment"] = "positive"
elif any(word in user_text_lower for word in ["hate", "don't like", "awful", "bad", "dislike", "not"]):
    interpretation["overall_sentiment"] = "negative"
```
**Why fallback must have the key:** If OpenAI is unavailable and the fallback omits `overall_sentiment`, `interpretation.overall_sentiment` is `undefined` (not `null`) in JavaScript after JSON deserialization. The SYNC-03 equality checks (`=== 'positive'`) would silently fail. Adding the key as `None` serializes to `null` in JSON, ensuring the key is always present.

---

### `backend/tests/test_ai_feedback_service.py` (Wave 0 + SYNC-01 tests)

**Change:** Extend existing `TestFeedbackInterpreter` class with two new test methods. Do NOT create a new file.

**Existing test class structure to follow** (lines 31–114) — copy the setUp/tearDown/patch pattern:
```python
class TestFeedbackInterpreter(unittest.TestCase):
    def setUp(self):
        self.mock_openai_patcher = patch('openai.OpenAI')
        self.mock_openai = self.mock_openai_patcher.start()
        from apps.ai.ai_feedback_service import FeedbackInterpreter
        self.FeedbackInterpreter = FeedbackInterpreter

    def tearDown(self):
        self.mock_openai_patcher.stop()
```

**Existing assertion style to copy** (lines 110–113):
```python
result = interpreter.interpret_feedback("I love fast music!")
self.assertIn("tempo_preference", result)
self.assertIn("confidence", result)
self.assertEqual(result["confidence"], 0.3)
```

**New test 1 — Wave 0 (must fail RED before SYNC-01):**
Add to `TestFeedbackInterpreter` class:
```python
def test_build_prompt_contains_overall_sentiment(self):
    """Test that _build_prompt schema includes overall_sentiment field"""
    with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
        mock_settings.OPENAI_API_KEY = None
        interpreter = self.FeedbackInterpreter()
        prompt = interpreter._build_prompt("test feedback")
        self.assertIn("overall_sentiment", prompt)
```

**New test 2 — Wave 0 (extend existing fallback test):**
Extend `test_interpret_feedback_fallback` (lines 100–114) to also assert the key is present, OR add a separate method:
```python
def test_fallback_interpretation_contains_overall_sentiment_key(self):
    """Test that fallback interpretation always includes overall_sentiment key"""
    self.mock_openai.side_effect = Exception("API Error")
    with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
        mock_settings.OPENAI_API_KEY = 'test-api-key'
        interpreter = self.FeedbackInterpreter()
        result = interpreter.interpret_feedback("I love fast music!")
        self.assertIn("overall_sentiment", result)
```
Run with: `cd backend && python -m pytest tests/test_ai_feedback_service.py -x`

---

## Shared Patterns

### React state declaration convention
**Source:** `frontend/app/profile/components/DailyGem/DailyGem.tsx` lines 37–41
**Apply to:** SYNC-03 (adding `aiSyncedFeedback`)
```typescript
const [gem, setGem] = useState<DailyGemResponse | null>(null);
const [loading, setLoading] = useState(true);
// ... co-located above component body
```
New state declared in the same block, not scattered through the component.

### useEffect with cleanup (addEventListener / removeEventListener)
**Source:** `frontend/app/profile/components/Feedback/FeedbackButtonGroup.tsx` lines 51–54 (trackId reset pattern) + standard React pattern
**Apply to:** EVOLVE-02 (`ImprovementStory.tsx`)
```typescript
useEffect(() => {
  const handler = () => fetchMetrics();
  window.addEventListener('songscope:new-gem', handler);
  return () => window.removeEventListener('songscope:new-gem', handler);
}, []);
```

### Named fetch function at component scope (not inside useEffect)
**Source:** `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` lines 35–47
**Apply to:** EVOLVE-02 (`ImprovementStory.tsx` — lift inline fetch chain to named function)
```typescript
const fetchMetrics = async () => {
  // fetch body
};

useEffect(() => {
  fetchMetrics();
}, []);
```

### get() import path and usage
**Source:** All four client components (`DailyGem.tsx` line 5, `ImprovementStory.tsx` line 4, `MetricsStrip.tsx` line 4, `TopArtists.tsx` line 5)
```typescript
import { get } from "../../../../services/axios";   // relative path
// or
import { get } from "@/services/axios";             // alias path (used in FeedbackButtonGroup, TopArtists)
```
Follow whichever import style the file already uses.

### try/catch/finally in async fetch functions
**Source:** `frontend/app/profile/components/DailyGem/DailyGem.tsx` lines 43–57
**Apply to:** All async fetch modifications
```typescript
try {
  // fetch + setState calls
} catch (err) {
  // error state
  console.error("...", err);
} finally {
  setLoading(false);
}
```

### Python unittest patch pattern
**Source:** `backend/tests/test_ai_feedback_service.py` lines 37–43, 88–93
**Apply to:** Wave 0 tests (SYNC-01)
```python
with patch('apps.ai.ai_feedback_service.settings') as mock_settings:
    mock_settings.OPENAI_API_KEY = None
    interpreter = self.FeedbackInterpreter()
    # assertions
```

---

## No Analog Found

None. All 9 files exist and were read directly. Every change is a surgical edit to existing code.

---

## Metadata

**Analog search scope:** All 9 target files read in full.
**Files scanned:** 9 target files + `tailwind.config.ts` (configuration verification)
**Pattern extraction date:** 2026-06-19
