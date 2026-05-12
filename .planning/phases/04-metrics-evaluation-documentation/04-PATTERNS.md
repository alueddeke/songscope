# Phase 4: Metrics, Evaluation & Documentation - Pattern Map

**Mapped:** 2026-05-12
**Files analyzed:** 10 new/modified files
**Analogs found:** 9 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/apps/core/views.py` (add `get_recommendation_metrics`) | view/controller | request-response, CRUD read | `views.py` `check_spotify_token` (lines 228–254) + `get_personalization_summary` (lines 359–370) | exact |
| `backend/apps/core/views.py` (add `get_recommendation_trend`) | view/controller | request-response, CRUD read | `views.py` `get_personalization_summary` (lines 359–370) | exact |
| `backend/config/urls.py` (add two paths) | config/routing | — | `urls.py` existing `path()` entries (lines 39–53) | exact |
| `backend/tests/test_metrics.py` | test | CRUD read / unit | `tests/test_recommendation_scoring.py` + `tests/test_feedback_learning.py` | exact |
| `frontend/app/profile/page.tsx` (wire MetricsStrip + new section) | server component | request-response (SSR) | `profile/page.tsx` existing structure (lines 1–72) | exact (modify) |
| `frontend/app/profile/components/LikeTrendChart/LikeTrendChart.tsx` | client component | request-response | `MetricsStrip.tsx` (lines 1–94) + `DailyGem.tsx` (lines 1–73) | role-match |
| `frontend/app/profile/components/TasteProfileChart/TasteProfileChart.tsx` | client component | request-response | `MetricsStrip.tsx` + `TopArtists.tsx` (lines 1–66) | role-match |
| `frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx` | client component | request-response | `MetricsStrip.tsx` | role-match |
| `frontend/app/profile/components/DiversityScore/DiversityScore.tsx` | client component | request-response | `MetricsStrip.tsx` | role-match |
| `CONCEPTS.md` + `SYSTEM_DESIGN.md` | static documentation | — | `INTERVIEW_PREP_SONGSCOPE.md` (repo root, 842 lines) | partial-match (same purpose, different format) |

---

## Pattern Assignments

### `backend/apps/core/views.py` — add `get_recommendation_metrics` (view, request-response)

**Analog:** `views.py` `check_spotify_token` (lines 228–254) for auth pattern; `get_personalization_summary` (lines 359–370) for the minimal try/except GET pattern.

**Imports pattern** (lines 1–32, already present — add only what is missing):
```python
# Already present:
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Track, RecommendationLog, DailyGem
from utils.logging_config import logger

# ADD to existing imports (not yet in views.py):
from django.db.models import Avg
from itertools import combinations
```

**Auth/decorator pattern** (views.py lines 228–230 — copy verbatim):
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendation_metrics(request):
```

**Minimal try/except core pattern** (views.py lines 359–370 — use as skeleton):
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_personalization_summary(request):
    """Get a summary of the user's personalization profile"""
    try:
        from apps.recommendations.personalization_engine import PersonalizationEngine
        personalization_engine = PersonalizationEngine(request.user)
        summary = personalization_engine.get_personalization_summary()
        return JsonResponse(summary)
    except Exception as e:
        logger.error(f"Error getting personalization summary: {str(e)}")
        return JsonResponse({'error': 'Failed to get personalization summary'}, status=500)
```

**Full metric computation pattern** — adapts the `get_track_recommendations` model (lines 256–343) for DB queryset work + `JsonResponse` return:
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendation_metrics(request):
    try:
        user = request.user
        gems = DailyGem.objects.filter(user=user).order_by('date')
        gem_list = list(gems.values('was_liked', 'track_popularity', 'date', 'track_id'))
        gem_total = len(gem_list)
        if gem_total == 0:
            return JsonResponse({'message': 'No gems yet'})

        gem_liked    = sum(1 for g in gem_list if g['was_liked'] is True)
        gem_disliked = sum(1 for g in gem_list if g['was_liked'] is False)
        gem_acceptance_rate = gem_liked / gem_total if gem_total > 0 else None
        avg_pop      = gems.aggregate(avg=Avg('track_popularity'))['avg'] or 0
        hidden_gem_rate = gems.filter(track_popularity__lt=40).count() / gem_total

        total_recommended = RecommendationLog.objects.filter(user=user).count()
        novel_track_rate  = hidden_gem_rate  # was_novel field unreliable; reuse

        from .models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        taste_vector  = profile.data.get('taste_vector', {})
        sorted_genres = sorted(taste_vector.items(), key=lambda x: x[1], reverse=True)
        top_genres    = [g for g, _ in sorted_genres[:10]]
        total_counts  = sum(c for _, c in sorted_genres[:10]) or 1
        top_genres_pct = [
            {'genre': g, 'pct': round(c / total_counts * 100, 1)}
            for g, c in sorted_genres[:10]
        ]

        first_7 = gem_list[:7]
        last_7  = gem_list[-7:]
        f7_liked = sum(1 for g in first_7 if g['was_liked'] is True)
        l7_liked = sum(1 for g in last_7  if g['was_liked'] is True)
        first_7_rate = round(f7_liked / len(first_7) * 100) if first_7 else None
        last_7_rate  = round(l7_liked / len(last_7)  * 100) if last_7  else None
        delta = (last_7_rate - first_7_rate) if (
            first_7_rate is not None and last_7_rate is not None
        ) else None

        track_ids = [g['track_id'] for g in gem_list]
        track_genres = {t.id: t.genres for t in Track.objects.filter(id__in=track_ids)}
        genre_lists  = [track_genres.get(tid, []) for tid in track_ids]
        nonempty     = [g for g in genre_lists if g]
        diversity_score = None
        if len(nonempty) >= 2:
            pairs     = list(combinations(nonempty, 2))
            distances = [
                1 - len(set(a) & set(b)) / len(set(a) | set(b))
                if set(a) | set(b) else 0.0
                for a, b in pairs
            ]
            diversity_score = round(sum(distances) / len(distances), 4)

        return JsonResponse({
            'total_recommended':   total_recommended,
            'avg_popularity':      round(avg_pop),
            'novel_track_rate':    novel_track_rate,
            'hidden_gem_rate':     round(hidden_gem_rate, 4),
            'gem_total':           gem_total,
            'gem_liked':           gem_liked,
            'gem_disliked':        gem_disliked,
            'gem_acceptance_rate': gem_acceptance_rate,
            'top_genres':          top_genres,
            'top_genres_pct':      top_genres_pct,
            'improvement_story':   {
                'first_7_rate': first_7_rate,
                'last_7_rate':  last_7_rate,
                'delta':        delta,
            },
            'diversity_score': diversity_score,
        })
    except Exception as e:
        logger.error(f"Error getting recommendation metrics: {str(e)}")
        return JsonResponse({'error': 'Failed to get recommendation metrics'}, status=500)
```

**Error handling pattern** (views.py lines 340–343 — copy structure):
```python
    except Exception as e:
        logger.exception("Unexpected error in get_recommendation_metrics")
        return JsonResponse({'error': 'Failed to get recommendation metrics'}, status=500)
```

---

### `backend/apps/core/views.py` — add `get_recommendation_trend` (view, request-response)

**Analog:** same as above — `get_personalization_summary` skeleton (lines 359–370).

**Core pattern:**
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendation_trend(request):
    try:
        from datetime import timedelta
        user = request.user
        gems = list(
            DailyGem.objects.filter(user=user)
            .order_by('date')
            .values('date', 'was_liked')
        )
        dates = sorted(set(g['date'] for g in gems))
        data_points = []
        for d in dates:
            window_start = d - timedelta(days=6)
            window = [g for g in gems if window_start <= g['date'] <= d]
            liked = sum(1 for g in window if g['was_liked'] is True)
            total = len(window)
            like_rate = round((liked / total) * 100, 1) if total > 0 else 0.0
            data_points.append({'date': str(d), 'like_rate': like_rate})
        if len(data_points) < 2:
            return JsonResponse({'data': [], 'message': 'Not enough data'})
        return JsonResponse({'data': data_points})
    except Exception as e:
        logger.error(f"Error getting recommendation trend: {str(e)}")
        return JsonResponse({'error': 'Failed to get recommendation trend'}, status=500)
```

---

### `backend/config/urls.py` — add two path entries (config/routing)

**Analog:** `urls.py` lines 39–53 — all existing API routes.

**Pattern** (copy the adjacent path entries exactly):
```python
# Source: backend/config/urls.py lines 39-53 — existing URL registration pattern
path('api/personalization-summary/', views.get_personalization_summary, name='personalization_summary'),
path('api/user-profile-summary/', views.get_user_profile_summary, name='user_profile_summary'),

# ADD after the existing api/get-user-name/ entry:
path('api/recommendation-metrics/', views.get_recommendation_metrics, name='recommendation_metrics'),
path('api/recommendation-trend/', views.get_recommendation_trend, name='recommendation_trend'),
```

---

### `backend/tests/test_metrics.py` (test, unit)

**Analog:** `tests/test_recommendation_scoring.py` (lines 1–80) for structure; `tests/test_feedback_learning.py` (lines 1–80) for django.test.TestCase + DB fixture pattern.

**File header + Django TestCase pattern** (test_feedback_learning.py lines 1–30):
```python
"""
Phase 4 tests: recommendation metrics endpoint, trend rolling window, Jaccard diversity.
"""
import unittest
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import Mock, patch

from apps.core.models import DailyGem, RecommendationLog, Track, UserProfile
```

**DB fixture setup pattern** (test_feedback_learning.py — uses `django.test.TestCase`, each test auto-rolled back):
```python
class TestMetricsEndpoint(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        # create DailyGem rows here using ORM

    def test_gem_acceptance_rate_null_when_no_gems(self):
        ...

    def test_hidden_gem_rate_uses_track_popularity_lt_40(self):
        ...
```

**Pure unit test pattern** (test_recommendation_scoring.py lines 53–80 — `unittest.TestCase`, no DB):
```python
class TestJaccard(unittest.TestCase):
    def test_jaccard_zero_both_empty(self):
        ...

    def test_jaccard_one_fully_disjoint(self):
        ...
```

**conftest.py is already wired** — `DJANGO_SETTINGS_MODULE = 'config.settings'` and `django.setup()` are called in `conftest.py`. New test file does not need to repeat this.

---

### `frontend/app/profile/page.tsx` — add MetricsStrip + new section (server component, modify)

**Analog:** `profile/page.tsx` lines 1–72 — the file being modified.

**Import addition pattern** (lines 1–5 — copy existing import style):
```tsx
// Source: profile/page.tsx lines 1-5
import { cookies } from 'next/headers'
import Image from 'next/image'
import { redirect } from 'next/navigation'
import Recommendation from './components/Recommendation/Recommendation'
import TopArtists from './components/TopArtists/TopArtists'

// ADD new imports — same relative path convention:
import MetricsStrip from './components/MetricsStrip/MetricsStrip'
import LikeTrendChart from './components/LikeTrendChart/LikeTrendChart'
import TasteProfileChart from './components/TasteProfileChart/TasteProfileChart'
import DiversityScore from './components/DiversityScore/DiversityScore'
import ImprovementStory from './components/ImprovementStory/ImprovementStory'
```

**Section wrapper pattern** (lines 61–67 — existing `<section>` blocks):
```tsx
// Source: profile/page.tsx lines 61-67
<section className="min-h-[100vh] flex justify-center items-center">
  <Recommendation />
</section>

<section className="py-64">
  <TopArtists/>
</section>
```

**New JSX to add after `<TopArtists/>` section** — mirrors the existing section layout:
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

**Critical constraint:** `page.tsx` is a server component — do NOT add `"use client"`, `useState`, or `useEffect` to this file. All client interactivity stays inside the imported components.

---

### `frontend/app/profile/components/LikeTrendChart/LikeTrendChart.tsx` (client component, request-response)

**Analog:** `MetricsStrip.tsx` (lines 1–94) for the fetch pattern; `DailyGem.tsx` (lines 58–73) for the loading state.

**"use client" + import block pattern** (MetricsStrip.tsx lines 1–5):
```tsx
// Source: MetricsStrip.tsx lines 1-5
"use client";

import { useState, useEffect } from "react";
import { get } from "../../../../services/axios";
```

**Interface definition pattern** (MetricsStrip.tsx lines 6–17):
```tsx
// Source: MetricsStrip.tsx lines 6-17
interface Metrics {
  total_recommended: number;
  // ...
  message?: string;
}
```

**Loading state pattern — 3 bouncing dots** (DailyGem.tsx lines 58–73):
```tsx
// Source: DailyGem.tsx lines 58-73
if (loading) {
  return (
    <div className="w-full min-h-[60vh] flex flex-col items-center justify-center gap-4">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-2 h-2 rounded-full bg-green animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
      <p className="text-gray-400 text-sm">Finding your gem for today…</p>
    </div>
  );
}
```

**Fetch + silent-fail pattern** (MetricsStrip.tsx lines 33–48):
```tsx
// Source: MetricsStrip.tsx lines 33-48
const fetchMetrics = async (showRefreshing = false) => {
  if (showRefreshing) setRefreshing(true);
  try {
    const data = await get<Metrics>("/api/recommendation-metrics/");
    setMetrics(data);
  } catch {
    // silently ignore — strip is informational
  } finally {
    setLoading(false);
    setRefreshing(false);
  }
};

useEffect(() => {
  fetchMetrics();
}, []);
```

**Full LikeTrendChart core pattern** (from RESEARCH.md Pattern 4, verified Recharts + Next.js 14):
```tsx
"use client";
import { useState, useEffect } from "react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { get } from "@/services/axios";

interface TrendPoint { date: string; like_rate: number; }
interface TrendResponse { data: TrendPoint[]; message?: string; }

export default function LikeTrendChart() {
  const [data, setData] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get<TrendResponse>("/api/recommendation-trend/")
      .then(r => setData(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return /* 3-dot bounce pattern from DailyGem.tsx lines 58-73 */;
  if (data.length < 2) return (
    <p className="text-gray-400 text-sm text-center py-8">
      Not enough data yet — your like-rate trend will appear after a few days of gems.
    </p>
  );

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid stroke="#374151" />
        <XAxis dataKey="date"
          tickFormatter={d => new Date(d).toLocaleDateString('en-US', {month:'short', day:'numeric'})}
          tick={{ fill: "#6b7280", fontSize: 12 }} />
        <YAxis domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 12 }} />
        <Tooltip formatter={(v: number) => `${v}%`} />
        <Line type="monotone" dataKey="like_rate" stroke="#1DB954" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

**Color token:** `stroke="#1DB954"` — verified from `frontend/tailwind.config.ts` line 23 (`green: "#1DB954"`).

---

### `frontend/app/profile/components/TasteProfileChart/TasteProfileChart.tsx` (client component, request-response)

**Analog:** `MetricsStrip.tsx` for fetch pattern; `TopArtists.tsx` for genre list rendering style.

**Fetch pattern:** identical to LikeTrendChart — call `/api/recommendation-metrics/`, extract `top_genres_pct` field, handle empty state.

**TopArtists genre rendering style** (TopArtists.tsx line 170):
```tsx
// Source: TopArtists.tsx line 170
<div className="text-xs text-gray-400">
  {artist.genres.slice(0, 2).join(', ')}
</div>
```

**Recharts horizontal BarChart pattern** (from RESEARCH.md Pattern 5, verified):
```tsx
"use client";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";
import { get } from "@/services/axios";

// data shape: [{genre: "indie pop", pct: 34.2}, ...]
<BarChart layout="vertical" data={data}>
  <XAxis type="number" domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 12 }} />
  <YAxis type="category" dataKey="genre" width={120} tick={{ fill: "#9ca3af", fontSize: 12 }} />
  <Bar dataKey="pct" fill="#1DB954" radius={[0, 3, 3, 0]} />
</BarChart>
```

**Empty-state pattern:** mirror MetricsStrip — `if (!data || data.length === 0) return null;`

---

### `frontend/app/profile/components/ImprovementStory/ImprovementStory.tsx` (client component, request-response)

**Analog:** `MetricsStrip.tsx` — both are stat-display components, no chart, pure data presentation.

**Stat display pattern** (MetricsStrip.tsx lines 19–26 — the `Stat` sub-component):
```tsx
// Source: MetricsStrip.tsx lines 19-26
function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 min-w-[100px]">
      <span className="text-green text-lg font-bold tabular-nums">{value}</span>
      <span className="text-gray-500 text-xs uppercase tracking-widest">{label}</span>
    </div>
  );
}
```

**Fetch pattern:** call `/api/recommendation-metrics/`, read `improvement_story.first_7_rate`, `improvement_story.last_7_rate`, `improvement_story.delta`. Display before/after with delta colored green (positive) or gray (negative/null).

**Full component shape:**
```tsx
"use client";
import { useState, useEffect } from "react";
import { get } from "@/services/axios";

interface MetricsResponse {
  improvement_story?: { first_7_rate: number|null; last_7_rate: number|null; delta: number|null; };
  message?: string;
}

export default function ImprovementStory() {
  const [story, setStory] = useState<MetricsResponse['improvement_story'] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get<MetricsResponse>("/api/recommendation-metrics/")
      .then(r => setStory(r.improvement_story ?? null))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading || !story || story.first_7_rate === null) return null;
  // render two Stat blocks + delta badge
}
```

---

### `frontend/app/profile/components/DiversityScore/DiversityScore.tsx` (client component, request-response)

**Analog:** `MetricsStrip.tsx` — single scalar display.

**Pattern:** identical structure to ImprovementStory. Fetch `/api/recommendation-metrics/`, read `diversity_score` float. If `null`, show a "Not enough data" message (expected when few gems have genre data).

**Silent null state** (mirrors MetricsStrip lines 50 — `if (!metrics || metrics.message) return null;`):
```tsx
if (loading || diversityScore === null) return null;
```

**Display:** render as a single `Stat`-style tile: label "Genre diversity", value `${(diversityScore * 100).toFixed(0)}%`. Include a tooltip or sub-label explaining the Jaccard interpretation.

---

### `CONCEPTS.md` + `SYSTEM_DESIGN.md` (static documentation, no analog)

**Closest reference:** `INTERVIEW_PREP_SONGSCOPE.md` (repo root, 842 lines) — existing interview doc that these complement.

**No direct code analog** — these are Markdown files. Structure is dictated by CONTEXT.md D-12 through D-15.

**CONCEPTS.md structure per D-14:** Each section follows `## [Algorithm Name]` → **Intuition** → **Formula** → **Code Snippet** (pulled from actual codebase) → **Interview Talking Point**.

**SYSTEM_DESIGN.md structure per D-13:** Mermaid diagram (GitHub-native rendering, no build step needed) + component descriptions.

See RESEARCH.md "Documentation Content Map" section for the full algorithm table and Mermaid skeleton.

---

## Shared Patterns

### Auth Guard (apply to all new backend views)

**Source:** `backend/apps/core/views.py` lines 228–230

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_name(request):
```

Apply to: `get_recommendation_metrics`, `get_recommendation_trend`.

---

### Error Handling (apply to all new backend views)

**Source:** `backend/apps/core/views.py` lines 359–370 (get_personalization_summary) and lines 340–343 (get_track_recommendations)

```python
    except Exception as e:
        logger.error(f"Error in <view_name>: {str(e)}")
        return JsonResponse({'error': 'Failed to <description>'}, status=500)
```

Apply to: both new views. Use `logger.error` not `print`. Import `logger` from `utils.logging_config` (already at line 32 of views.py).

---

### Frontend Fetch + Silent-Fail (apply to all new client components)

**Source:** `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` lines 33–48

```tsx
useEffect(() => {
  get<ResponseType>("/api/endpoint/")
    .then(r => setData(r.field || defaultValue))
    .catch(() => {})          // silent fail — informational component
    .finally(() => setLoading(false));
}, []);
```

Apply to: LikeTrendChart, TasteProfileChart, ImprovementStory, DiversityScore.

---

### "use client" + useState/useEffect Shell (apply to all new client components)

**Source:** `frontend/app/profile/components/MetricsStrip/MetricsStrip.tsx` lines 1–4 and `DailyGem.tsx` lines 1–3

```tsx
"use client";

import { useState, useEffect } from "react";
import { get } from "@/services/axios";  // or relative path ../../../../services/axios
```

Apply to: all four new chart/stat components.

---

### Loading State — 3 Bouncing Dots (apply to chart components)

**Source:** `frontend/app/profile/components/DailyGem/DailyGem.tsx` lines 58–73

```tsx
if (loading) {
  return (
    <div className="flex gap-1 justify-center py-8">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="w-2 h-2 rounded-full bg-green animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
```

Apply to: LikeTrendChart, TasteProfileChart. For ImprovementStory and DiversityScore (scalar displays), return `null` during loading per MetricsStrip convention.

---

### URL Registration (apply to urls.py additions)

**Source:** `backend/config/urls.py` lines 39–53

```python
path('api/<endpoint-name>/', views.<view_function>, name='<snake_case_name>'),
```

No trailing slash omission — all existing URLs include trailing slash. New paths must match.

---

### Test File Structure (apply to test_metrics.py)

**Source:** `backend/tests/test_recommendation_scoring.py` lines 1–80 + `tests/conftest.py`

- `conftest.py` already handles `DJANGO_SETTINGS_MODULE` and `django.setup()` — do not repeat in test file.
- Use `django.test.TestCase` for tests requiring DB (DailyGem/UserProfile creation).
- Use `unittest.TestCase` for pure math helpers (Jaccard distance function).
- Class naming convention: `TestMetricsEndpoint`, `TestTrendEndpoint`, `TestJaccard`, `TestTasteVector`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `CONCEPTS.md` | static doc | — | No ML concept documentation exists in the repo; closest reference is INTERVIEW_PREP_SONGSCOPE.md but it is a Q&A format, not intuition+formula+code format |
| `SYSTEM_DESIGN.md` | static doc | — | No Mermaid architecture diagram exists in the repo; RESEARCH.md provides the Mermaid skeleton |

---

## Metadata

**Analog search scope:** `backend/apps/core/views.py`, `backend/config/urls.py`, `backend/tests/`, `frontend/app/profile/`, `frontend/services/axios.ts`
**Files read directly:** 10
**Pattern extraction date:** 2026-05-12
