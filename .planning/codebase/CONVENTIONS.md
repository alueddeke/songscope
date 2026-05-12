# Coding Conventions

_Last updated: 2026-05-06_

## Summary

SongScope uses TypeScript with React (Next.js 14 App Router) on the frontend and Python with Django REST Framework on the backend. The frontend has TypeScript strict mode enabled and ESLint via `next/core-web-vitals`. There is no Prettier config, no Biome config, and no Python formatter config (no Black, no isort, no Ruff). Conventions are partially enforced by tooling and partially informal. Component structure is consistent but type safety has gaps (`any` appears in several places). Python files use standard Django/DRF patterns with `logging.getLogger(__name__)` throughout.

---

## Frontend Conventions

### File Naming

- Component files: PascalCase matching the component name — `FeedbackButton.tsx`, `DailyGem.tsx`, `MetricsStrip.tsx`
- Component directories: PascalCase — `frontend/app/profile/components/Feedback/`, `frontend/app/profile/components/DailyGem/`
- Service files: camelCase — `frontend/services/axios.ts`
- Config files: camelCase or dot-prefixed — `tailwind.config.ts`, `tsconfig.json`, `postcss.config.mjs`

### Component Patterns

All components are function components. No class components exist. Every component that uses state, effects, or browser APIs carries the `'use client'` directive at the very top of the file.

**Default export vs. named export:**
- Page-level and feature components use `export default function ComponentName(...)`
- Utility/shared components can use named exports: `export function AudioPlayer(...)`, `export function AddToLiked(...)`
- Types and constants exported alongside components: `export type FeedbackType`, `export const feedbackConfig`

**Props pattern:**
All components define a co-located `interface ComponentNameProps` directly above the component function. Props are destructured inline in the function signature:
```typescript
interface FeedbackButtonGroupProps {
  trackId: string;
  onTrackRemoved?: () => void;
}

export default function FeedbackButtonGroup({ trackId, onTrackRemoved }: FeedbackButtonGroupProps) {
```

**State initialization:**
`useState` always typed explicitly when the initial value would otherwise be inferred as `null` or `any`:
```typescript
const [error, setError] = useState<string | null>(null);
const [loading, setLoading] = useState<boolean>(true);
const [recommendations, setRecommendations] = useState<Track[]>([]);
```

### TypeScript Usage

- `tsconfig.json` has `"strict": true` enabled.
- Path alias `@/*` maps to the frontend root (`./*`).
- Both `@/services/axios` and relative paths (`../../../../services/axios`) are used for the same import — inconsistent.
- `any` appears in several places where AI interpretation data lacks a typed interface:
  - `frontend/app/profile/components/Feedback/AIFeedbackInput.tsx` — `interpretation: any`, `onFeedbackSubmitted?: (interpretation: any) => void`
  - `frontend/app/profile/components/TopArtists/TopArtists.tsx` — `expandedArtistData: any`
  - `frontend/services/axios.ts` — `post<T>(url: string, data: any)`
- `err: any` used in catch blocks where `err instanceof Error` checks would be more type-safe.

### Import Order

No enforced order rule. Observed pattern in components:
1. React/Next.js imports (`'use client'` directive first, then React hooks)
2. Internal services (`@/services/axios` or relative path)
3. Third-party icon libraries (`lucide-react`)
4. Local component imports (relative paths)

### Async/Error Handling

All data fetching follows the same pattern: `try/catch/finally` with explicit loading and error state:
```typescript
const fetchData = async () => {
  try {
    setLoading(true);
    setError(null);
    const data = await get<ResponseType>(url);
    setState(data);
  } catch (err) {
    setError("Human-readable message");
    console.error("Debug message:", err);
  } finally {
    setLoading(false);
  }
};
```

HTTP status-specific error messages are handled by string matching in `Recommendation.tsx` (checks for `"401"`, `"403"`, `"404"`, `"500"` in `err.message`). This is fragile; most other components use a single catch-all error string.

### Styling

- Tailwind CSS is the primary styling system. No CSS modules, no SCSS modules. One global CSS file at `frontend/styles/globals.css` contains only Tailwind directives and three `@keyframes` animation declarations.
- Custom color tokens in `tailwind.config.ts`: `dark`, `navy`, `orange`, `light-gray`, `brown`, `green` (Spotify green `#1DB954`).
- Inline `className` strings with conditional logic are common — template literals and ternaries used for dynamic classes:
  ```tsx
  className={`w-full px-4 py-2 bg-gray-800 text-white ... ${isPlaceholderTransitioning ? 'placeholder-transition' : ''}`}
  ```
- Responsive classes follow Tailwind convention: `flex-col md:flex-row`, `text-2xl lg:text-5xl`.

### Console Logging

20 `console.log` / `console.error` calls exist in the frontend source. Several are debug-only statements left in production code (e.g., `console.log("Fetching recommendations from API...")`, `console.log("Backend URL:", ...)`, `console.log("Current cookies:", document.cookie)` in `Recommendation.tsx`). These should be removed before production.

---

## Backend Conventions

### File Naming

- Python modules: `snake_case` — `ai_feedback_service.py`, `hybrid_recommendation_engine.py`, `feature_extractor.py`
- Django apps: `snake_case` — `apps/core/`, `apps/ai/`, `apps/recommendations/`, `apps/spotify/`
- Test files: `test_<feature>.py` — `test_ai_feedback_service.py`, `test_openai_integration.py`

### Logging

All backend modules use the standard Django logger pattern at the module level:
```python
import logging
logger = logging.getLogger(__name__)
```
`views.py` imports a custom logger from `utils/logging_config.py` (`from utils.logging_config import logger, log_api_error, log_spotify_error`) but then immediately re-assigns it: `logger = logging.getLogger(__name__)` — a bug that silently ignores the custom logger.

### Type Hints

Python type hints used consistently in service classes and recommendation engines with `typing` imports:
```python
from typing import Dict, Optional, List, Any, Tuple
def interpret_feedback(self, feedback_text: str) -> Dict:
```
Not used in `views.py` function signatures.

### Docstrings

Classes and modules have docstrings. View functions do not. Example:
```python
"""
AI Feedback Service - OpenAI-powered feedback interpretation
...
"""
class RateLimitMonitor:
    """Monitor OpenAI API rate limits and costs"""
```

### Django Patterns

- Views use `@api_view`, `@login_required`, `@require_http_methods` decorators.
- Authentication is `SessionAuthentication` with a custom `CsrfExemptSessionAuthentication` subclass that skips CSRF enforcement.
- Model methods: `__str__` defined on all models; business logic methods on models where appropriate (e.g., `UserProfile.get_from_cache()`).
- `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'` is set at the top of `views.py` unconditionally — this disables HTTPS requirement for OAuth even in production.

### No Formatter Enforced

No `.prettierrc`, no `black`, no `isort`, no `ruff` config files exist in the project. Code formatting is manual and inconsistent — single quotes used in some frontend files (`'use client'`), double quotes in others.

---

## Linting Configuration

**Frontend:**
- ESLint config: `/.eslintrc.json` — extends `next/core-web-vitals` only. No additional rules.
- Run command: `npm run lint` (calls `next lint`)
- No Prettier configured.

**Backend:**
- No linting config detected (no `.flake8`, no `pyproject.toml`, no `setup.cfg`, no `ruff.toml`).

---

## Key Observations

- `'use client'` directive is present on all components that use state or effects — correctly applied throughout.
- Props interfaces are always defined co-located with their component, never in a separate `types/` file.
- The `@/*` path alias and relative imports (`../../../../`) are used interchangeably for the same `services/axios` module — should be standardised to `@/services/axios`.
- `any` type is used for AI interpretation payloads in `AIFeedbackInput.tsx` and `TopArtists.tsx`; a typed interface for the OpenAI response structure is missing.
- `post<T>(url, data: any)` in `frontend/services/axios.ts` weakens the typed API client.
- Debug `console.log` statements including `document.cookie` exposure remain in `Recommendation.tsx`.
- `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'` in `backend/apps/core/views.py` is unconditional — must be gated to development only.
- No Prettier or Black enforced — formatting consistency relies on developer discipline.
- The `logger` in `views.py` is imported from a custom utility then immediately overwritten by `logging.getLogger(__name__)`.
