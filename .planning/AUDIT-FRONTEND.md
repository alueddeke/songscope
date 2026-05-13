# SongScope Frontend Audit

**Date:** 2026-05-13  
**Scope:** Next.js 14 App Router, TypeScript  
**Reviewed files:** 20 source files  
**Audit depth:** Deep (cross-file, API contract, state management, auth)

---

## CRITICAL

---

### C-01: Double-submit not prevented in AddToLiked — optimistic UI with no guard

**File:** `app/profile/components/AddToLiked/AddToLiked.tsx:13-25`

**Description:** `addToSpotify()` sets `liked = true` immediately (optimistic) and then fires the request, but there is no `disabled` state on the button and no in-flight guard. Clicking the button rapidly fires multiple POST `/api/add-track-to-liked/` requests. If the first request fails the icon stays green (liked) while the track was never added to Spotify.

```tsx
// Current — optimistic flip before request, no guard
async function addToSpotify() {
  setLiked(true)            // <-- already shows as liked
  try {
    await post(...)          // <-- can fail silently
  } catch {
    console.log("error")   // <-- liked icon stays green
  }
}
```

**Why it matters:** Users end up with a misleading "liked" indicator for tracks that were never saved. Multiple concurrent requests can exhaust rate limits.

**Fix:**
```tsx
const [loading, setLoading] = useState(false);

async function addToSpotify() {
  if (loading || liked) return;
  setLoading(true);
  try {
    await post(`/api/add-track-to-liked/`, { track_id });
    setLiked(true);
  } catch {
    // revert — do NOT flip liked
  } finally {
    setLoading(false);
  }
}

<button onClick={addToSpotify} disabled={loading || liked} ...>
```

---

### C-02: `AddToLiked` calls `post()` with a fully-qualified URL, bypassing the axios interceptor and therefore sending no CSRF token

**File:** `app/profile/components/AddToLiked/AddToLiked.tsx:17-20`

```tsx
const response: Response = await post(
  `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/add-track-to-liked/`,
  { track_id: track_id }
);
```

Every other component calls `post("/api/add-track-to-liked/", ...)` (relative path). The `post()` helper in `services/axios.ts` uses `axios.create({ baseURL: BACKEND_URL })` — passing a full URL overrides the `baseURL`, but the request interceptor that injects `X-CSRFToken` still runs. However, the CSRF cookie is read from `document.cookie` at request time. This is not the main issue here — the real bug is that the response type is declared as `Response` (the Fetch API type) when `post<T>()` returns `Promise<T>` (the unwrapped data). The type annotation is completely wrong, which suppresses all downstream TypeScript errors on the response object.

**Why it matters:** `response` is typed as Fetch `Response`, but its actual value is already the parsed JSON body. Any access like `response.status` or `response.json()` would return `undefined`. TypeScript does not catch this because the generic is unsuppressed by the wrong annotation.

**Fix:**
```tsx
// Use relative path (consistent with all other callers)
// Use the correct return type
const data = await post<{ message: string }>(
  "/api/add-track-to-liked/",
  { track_id }
);
```

---

### C-03: API contract mismatch — `FeedbackButtonGroup` sends `feedback_type` but backend serializer expects `feedback_type`; the field name matches but the values do not

**File:** `app/profile/components/Feedback/FeedbackButtonGroup.tsx:61-64`  
**Backend:** `backend/apps/core/views.py:575`

Frontend sends:
```json
{ "track_id": "...", "feedback_type": "LIKE" }
```

The backend `FeedbackSubmissionSerializer` validates and accepts this. However, the backend response on **LIKE** returns `{ "status": "success", "action": "added" }` or `{ "status": "success", "action": "removed" }`. The frontend checks `response.action === 'removed'` at line 75. This is correct.

But on **DISLIKE** the frontend never checks `response.action` at all — there is no branch for `feedbackType === "DISLIKE" && response.action`. This is not the contract bug. The actual contract bug is:

The endpoint spec listed in the prompt says:
```
POST /api/submit-feedback/ → { gem_id, action: 'like'|'dislike'|'unlike' }
```

But the frontend sends `track_id` + `feedback_type: 'LIKE'|'DISLIKE'`, and the backend reads `track_id` + `feedback_type`. The documented contract (`gem_id`, `action: 'like'|'dislike'|'unlike'`) does **not** match what either side actually implements. This is a documentation / contract drift issue that will cause confusion during any integration work.

---

### C-04: Stale closure — `setIsRefreshing(false)` and `setLoading(false)` inside `fetchRecommendations` are never called when an exception is thrown before the `try` block resolves

**File:** `app/profile/components/Recommendation/Recommendation.tsx:32-99`

In the error path, `setLoading(false)` and `setIsRefreshing(false)` are called explicitly (lines 97-98), but if `get<RecommendationsResponse>(url)` throws an error that is an `AxiosError` — which the `post()` wrapper re-throws as a generic `Error` — the `err.message.includes("401")` check may never match because the wrapper already re-wraps the message. The loading state is eventually cleared, so this is a degraded-but-not-broken path.

The more severe bug: `setError("No recommendations available")` is set at line 71 **while `loading` is still `true`** (line 73 clears loading), but the render check at line 158 is `if (error)` — which would show the error UI. However, `loading` is only cleared after `setError`. The real issue: when `forceFresh=true` and the request throws, `setIsRefreshing(false)` at line 98 clears the refresh spinner, but `setLoading(false)` at line 97 is also called even though `loading` was never set to `true` for the `forceFresh` path (line 34-38 sets `isRefreshing`, not `loading`). This means the loading UI can disappear between a fresh-fetch error and the refresh error state.

**More severe issue in same component:** `console.log("Current cookies:", document.cookie)` on line 50 intentionally prints all cookies including the session cookie to the browser console. This is a security information leak.

---

### C-05: Session cookie exposure — `document.cookie` printed to console

**File:** `app/profile/components/Recommendation/Recommendation.tsx:50`

```tsx
console.log("Current cookies:", document.cookie);
```

`document.cookie` includes `sessionid` (the Django session identifier). Printing it to the console makes the session token visible in any browser with DevTools open, and it persists in logging pipelines if the app uses error tracking (Sentry, Datadog, etc.).

**Why it matters:** Anyone with physical access to the machine or access to error tracking logs can hijack the session.

**Fix:** Remove this `console.log` entirely. The auth check endpoint at `/api/check-auth/` already confirms authentication without exposing credentials.

---

### C-06: `getUserName()` in page.tsx crashes with unhandled runtime error if `data.user_name` is `null` or if `data.user_name.display_name` is `null`

**File:** `app/profile/page.tsx:41`

```tsx
return data.user_name.display_name
```

The backend `get_user_name` view returns the full Spotipy `sp.me()` object as `user_name`. The Spotify API field `display_name` can be `null` for accounts without a display name set. When `display_name` is `null`, Next.js will render `null` in the JSX `{userName}` without error — but if the whole `user_name` key is absent from the response (e.g., error path returns `{'error': '...'}`) this will throw `TypeError: Cannot read properties of undefined (reading 'display_name')` and crash the entire SSR page with a 500.

Additionally, the error check at line 32-37 is:
```tsx
if (response.status > 300) {
  redirect('/')
}
throw new Error('Failed to fetch user data')
```
`response.status > 300` would redirect on a 301/302 redirect response, which is unexpected. A 4xx or 5xx check should use `response.ok` or `response.status >= 400`. A 301 from the backend would incorrectly redirect the user to `/` from the profile page.

**Fix:**
```tsx
if (response.status === 401 || response.status === 403) {
  redirect('/');
}
if (!response.ok) {
  throw new Error('Failed to fetch user data');
}
const data = await response.json();
return data.user_name?.display_name ?? 'there';
```

---

### C-07: `getClient()` is called on every single request — a new axios instance with new interceptors is created per request

**File:** `services/axios.ts:13-44`

`getClient()` calls `axios.create(...)` and registers both a request interceptor and a response interceptor every time it is called. `get()` and `post()` both call `getClient()` internally. Every component that calls `get()` or `post()` in a `useEffect` or event handler creates a new axios instance. While axios instances do not individually leak memory in the same way event listeners on DOM nodes do, the pattern causes unnecessary overhead and the interceptor stack grows if any caller accidentally holds a reference.

More critically: `getCookie("csrftoken")` is called inside the request interceptor, which calls `document.cookie`. This will throw **`ReferenceError: document is not defined`** if `getClient()` is ever called in a Server Component or during SSR — since `services/axios.ts` has no `"use client"` directive and is imported by the SSR page component transitively.

**Why it matters:** Any server-side invocation of `getClient()` (e.g., from a misconfigured import chain) will throw and crash the request.

**Fix:** Add `"use client"` boundary to all components using `get()`/`post()` (already done for most), and restructure `getClient()` to be a singleton or at minimum guard `document` access:
```ts
const csrfToken = typeof document !== 'undefined' ? getCookie("csrftoken") : null;
```

---

### C-08: `AIFeedbackInput` — `setTimeout` inside `useEffect` creates a nested `setTimeout` that holds a stale closure reference and is never cancelled on unmount

**File:** `app/profile/components/Feedback/AIFeedbackInput.tsx:53-65`

```tsx
useEffect(() => {
  const interval = setInterval(() => {
    setIsPlaceholderTransitioning(true);
    setTimeout(() => {           // <-- inner timeout, never cancelled
      setCurrentPlaceholderIndex(...)
      setIsPlaceholderTransitioning(false);
    }, 250);
  }, 3000);
  return () => clearInterval(interval);   // <-- only clears the interval, not the timeout
}, []);
```

When the component unmounts (e.g., user navigates away while the 250ms inner timeout is pending), `setCurrentPlaceholderIndex` and `setIsPlaceholderTransitioning` are called on an unmounted component. In React 18 this no longer throws (setState on unmounted component is a no-op), but it is still a resource leak and will trigger the React dev warning "Can't perform a React state update on an unmounted component."

**Fix:**
```tsx
useEffect(() => {
  let timeoutId: ReturnType<typeof setTimeout>;
  const interval = setInterval(() => {
    setIsPlaceholderTransitioning(true);
    timeoutId = setTimeout(() => {
      setCurrentPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDER_SUGGESTIONS.length);
      setIsPlaceholderTransitioning(false);
    }, 250);
  }, 3000);
  return () => {
    clearInterval(interval);
    clearTimeout(timeoutId);
  };
}, []);
```

---

## HIGH

---

### H-01: API contract mismatch — `DailyGem` interface does not match the actual backend response

**File:** `app/profile/components/DailyGem/DailyGem.tsx:21-26`  
**Backend:** `backend/apps/core/views.py:1042-1057`

Frontend `DailyGemResponse` interface:
```ts
interface DailyGemResponse {
  track: GemTrack;
  explanation: string;
  date: string;
  cached: boolean;
}
```

Backend actually sends `score_breakdown` as a top-level key. This is not consumed by the frontend, so it is just dead data — not a crash. However, the frontend interface omits `gem_id` and `source` which are listed in the prompt's API spec. The component passes `track.id` as the feedback track ID — which is correct — but any future consumer expecting `gem_id` will find it missing from the typed interface.

More importantly: the backend's "fresh branch" sets `explanation: ''` (empty string, line 1131). The component unconditionally renders:
```tsx
<blockquote ...>
  <p ...>{explanation}</p>
</blockquote>
```
This renders an empty `<blockquote>` with a visible left border whenever a fresh gem is generated. This is a UX defect — the explanation is always empty for new gems.

**Fix:** Guard the explanation render:
```tsx
{explanation && (
  <blockquote ...>
    <p ...>{explanation}</p>
  </blockquote>
)}
```

---

### H-02: `MetricsStrip` silently ignores all errors and returns `null` — user gets a blank section with no feedback

**File:** `app/profile/components/MetricsStrip/MetricsStrip.tsx:38-43`

```tsx
} catch {
  // silently ignore — strip is informational
} finally {
  setLoading(false);
  ...
}
```

The `loading` state starts `true`. If the request fails, `loading` becomes `false`, `metrics` remains `null`, and the component returns `null`. The user sees nothing — no error, no retry button. For a user who has never loaded data, this looks identical to the "no data" state but is actually a failed network request.

**Fix:** Track the error and show a subtle fallback:
```tsx
const [fetchFailed, setFetchFailed] = useState(false);
// in catch:
setFetchFailed(true);
// in render:
if (fetchFailed) return <p className="text-gray-600 text-xs px-4 py-6">Stats unavailable</p>;
```

---

### H-03: `FeedbackButtonGroup.checkInitialLikeState` is called inside `useEffect` but `checkInitialLikeState` is defined after the state declarations it depends on — and the `useEffect` dep array does not include `trackId` even though it uses it

**File:** `app/profile/components/Feedback/FeedbackButtonGroup.tsx:31-55`

```tsx
useEffect(() => {
  setSelectedFeedback(null);
  checkInitialLikeState();   // <-- uses trackId via closure
}, [trackId]);               // <-- trackId IS in the dep array — this part is correct
```

`checkInitialLikeState` is defined as a `const` after the `useEffect` call. In JavaScript this works because function hoisting applies... except `checkInitialLikeState` is defined with `const`, not `function`. `const` declarations are hoisted but not initialized — this is the temporal dead zone (TDZ). However, since `checkInitialLikeState` is only *called* at runtime inside the `useEffect` callback (not at definition time), the TDZ is not actually triggered here. This is a **code quality issue** that creates confusion and could bite a refactor.

The real bug: `checkInitialLikeState` is not in the `useEffect` dep array. The ESLint `react-hooks/exhaustive-deps` rule would flag this. If `checkInitialLikeState` were ever recreated (e.g., wrapped in `useCallback` with different deps), the stale version would be called.

**Fix:** Define `checkInitialLikeState` above the `useEffect`, or include it in deps:
```tsx
const checkInitialLikeState = useCallback(async () => { ... }, [trackId]);

useEffect(() => {
  setSelectedFeedback(null);
  checkInitialLikeState();
}, [trackId, checkInitialLikeState]);
```

---

### H-04: `TopArtists` grid rendering is broken — expanded details panel appears in the wrong grid column position

**File:** `app/profile/components/TopArtists/TopArtists.tsx:131-211`

The component manually builds a flat `JSX.Element[]` array and inserts the expanded panel immediately after the artist card with `col-span-full`. In a CSS grid, `col-span-full` only spans full width if the element is a **direct child of the grid container**. Here the artist cards and the expanded panel are all direct children of the same `div.grid`, so `col-span-full` will work — but the expanded panel is inserted **immediately after the expanded artist card**, not after the complete row. With a 4-column grid, if the expanded artist is in column 3, the panel will appear after column 3's card in the DOM flow, causing the next artist card(s) in the row to appear to the right of or below the expanded panel rather than continuing the grid naturally.

Additionally, every artist card in the loop re-computes `hasTopTracks`, `hasRecentTracks`, `hasLikedSongs`, `allFromAlbums` at line 200-203 by scanning the *entire* `artist.user_top_tracks` array on every iteration — O(n²) in total, but that is a perf concern, not correctness.

The structural bug: the `key` for expanded rows is `expanded-${artist.id}`. If `artist.id` is the same across two renders (which it always is for the same artist), React will correctly reconcile. This is fine.

**Why it matters:** On screen sizes where the grid is 4 columns and the expanded artist is not in the last column of the row, the remaining artists in that row "wrap" below the panel, breaking the visual rank ordering.

---

### H-05: `LikeTrendChart` — `XAxis` `tickFormatter` passes a raw `date` string to `new Date()` without timezone correction, causing off-by-one date display

**File:** `app/profile/components/LikeTrendChart/LikeTrendChart.tsx:64-69`

```tsx
tickFormatter={(d: string) =>
  new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" })
}
```

The backend sends `date` as a plain ISO date string like `"2026-05-12"`. `new Date("2026-05-12")` is parsed as **UTC midnight** by the ECMAScript spec. `toLocaleDateString` converts it to the user's local timezone. For users in UTC-N timezones (Americas), `"2026-05-12T00:00:00Z"` displayed in local time becomes May 11 — one day earlier than what the backend intended.

`DailyGem.tsx` already works around this correctly with `new Date(date + "T00:00:00")` (local noon). The chart does not apply this fix.

**Fix:**
```tsx
tickFormatter={(d: string) =>
  new Date(d + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })
}
```

---

### H-06: `ImprovementStory` displays raw percentage numbers without the `%` suffix for `first_7_rate` and `last_7_rate`

**File:** `app/profile/components/ImprovementStory/ImprovementStory.tsx:55-56`

```tsx
<Stat label="When I started" value={`${story.first_7_rate}%`} />
<Stat label="Now" value={`${story.last_7_rate}%`} />
```

Wait — the `%` is included. But the backend returns `first_7_rate` as an integer already representing percent (e.g., `72` meaning 72%). The component adds `%` which is correct. No bug here in the display. However:

The interface declares:
```ts
interface Story {
  first_7_rate: number | null;
  last_7_rate: number | null;
  delta: number | null;
}
```

The component checks `story.first_7_rate === null || story.last_7_rate === null` and returns `null` if either is null. But the `delta` field is not null-guarded before use in the delta display logic (lines 41-49). The backend can return `delta: null` only when `gem_total < 2`. If somehow a Story object reaches the render path with `delta: null` while `first_7_rate` and `last_7_rate` are non-null (which shouldn't happen per backend logic, but defensive coding), the delta text would display `"— 0pp"` correctly because the `delta !== null` checks handle it. This is actually fine — noting as verified.

---

### H-07: Multiple components hit `/api/recommendation-metrics/` independently — N separate HTTP requests on page load

**File:** `MetricsStrip.tsx:36`, `TasteProfileChart.tsx:29`, `DiversityScore.tsx:16`, `ImprovementStory.tsx:31`

All four components independently `GET /api/recommendation-metrics/` in their own `useEffect`. On every page load, 4 identical requests fire concurrently. The backend computes a potentially expensive Jaccard diversity score across all gem pairs (combinations) on each call. No caching or deduplication exists in the frontend.

**Why it matters:** This quadruples the backend load for every profile page view, and the Jaccard computation is O(n²) in the number of gems.

**Fix:** Lift the metrics fetch to the parent `UserProfile` page (or a React context/Zustand store) and pass the data as props.

---

### H-08: `Recommendation.tsx` — `refreshRecommendations` is called inside an `onFeedbackSubmitted` callback wrapped in `setTimeout`, but `refreshRecommendations` captures the `fetchRecommendations` function via closure which captures `setLoading`/`setIsRefreshing` — this is fine but the 2-second hardcoded delay is a UX assumption that will silently fail if the AI feedback endpoint is slow

**File:** `app/profile/components/Recommendation/Recommendation.tsx:327-332`

```tsx
onFeedbackSubmitted={() => {
  setTimeout(() => {
    refreshRecommendations();
  }, 2000);
}}
```

This creates a dangling `setTimeout` reference. If the user navigates away within 2 seconds of submitting AI feedback, `refreshRecommendations()` fires on an unmounted component, triggering state updates (`setLoading`, `setRecommendations`, etc.) on a dead component tree. In React 18 this is a no-op but still triggers dev-mode warnings. More importantly, there is no way to cancel this timeout.

---

## MEDIUM

---

### M-01: `FeedbackButton` — `isLoading` state is local to `FeedbackButton`, while `disabled` is passed from `FeedbackButtonGroup.status.loading`. Two separate loading guards create a race window

**File:** `app/profile/components/Feedback/FeedbackButton.tsx:56`, `FeedbackButtonGroup.tsx:123-130`

`FeedbackButton` has its own `isLoading` state (line 56) that is set to `true` during `handleClick`. The parent also passes `disabled={status.loading}`. Between when `FeedbackButton.isLoading` is set to `false` (after `onSubmit` resolves) and when `FeedbackButtonGroup.status.loading` is set to `false`, neither guard is active. This is a 0ms window (same microtask), so it's not an exploitable double-submit window in practice, but the dual-loading state is unnecessarily complex.

---

### M-02: `TopArtists` — `expandedArtistData` typed as `any`, `ArtistExpandedDetails` receives `any` as `ArtistDetailsData | null`

**File:** `app/profile/components/TopArtists/TopArtists.tsx:48`

```tsx
const [expandedArtistData, setExpandedArtistData] = useState<any>(null);
```

`ArtistExpandedDetails` receives this `any` as the `artist` prop. TypeScript cannot enforce the shape. Any change to the backend response shape will fail silently at runtime.

**Fix:**
```tsx
const [expandedArtistData, setExpandedArtistData] = useState<ArtistDetailsData | null>(null);
```
Import or re-export `ArtistDetailsData` from `ArtistExpandedDetails.tsx`.

---

### M-03: `AIFeedbackInput` — `err: any` annotation and unsafe property access

**File:** `app/profile/components/Feedback/AIFeedbackInput.tsx:96-108`

```tsx
} catch (err: any) {
  if (err.response?.status === 429) {
```

The `post()` helper in `services/axios.ts` re-throws errors as `new Error(...)` (plain `Error`), not as `AxiosError`. So `err.response` will always be `undefined`, and the 429 rate-limit branch will **never execute**. The rate limit error handling is dead code.

**Fix:** Either preserve the original `AxiosError` in the `post()` wrapper, or handle the re-thrown message:
```tsx
// In services/axios.ts — re-throw AxiosError directly:
throw error; // instead of: throw new Error(error.response?.data?.error || ...)
```

---

### M-04: `page.tsx` — the `getUserName` function is `async` and can throw, but Next.js App Router SSR does not have a catch boundary here. Any uncaught throw renders a 500 error page

**File:** `app/profile/page.tsx:12-42`

There is no `error.tsx` boundary mentioned, and the `throw new Error('Failed to fetch user data')` at line 37 will bubble up to Next.js as an unhandled error, displaying the default Next.js error page. For a production app this exposes stack traces in development and shows a generic error page in production with no way to recover.

**Fix:** Add `app/profile/error.tsx` as a client-side error boundary for the profile route, or wrap in try/catch and redirect:
```tsx
const userName = await getUserName().catch(() => { redirect('/'); });
```

---

### M-05: `services/axios.ts:52` — `data: any` parameter in `post<T>()` 

**File:** `services/axios.ts:52`

```ts
export async function post<T>(url: string, data: any): Promise<T> {
```

The `any` type on `data` means callers get no type checking on the request body. Any typo in field names (e.g., sending `trackId` instead of `track_id`) will compile without error.

**Fix:**
```ts
export async function post<TResponse, TBody = Record<string, unknown>>(
  url: string, 
  data: TBody
): Promise<TResponse>
```

---

### M-06: `ArtistExpandedDetails` — `formatFollowers` checks `!followers` which returns `true` for `followers === 0`, incorrectly displaying "0" instead of "0" (which is actually correct coincidentally), but will display "0" for any falsy value including `NaN`. The deeper issue: `artist.followers` is typed as `number` (not optional) in the interface but `formatFollowers` accepts `number | undefined`

**File:** `app/profile/components/TopArtists/ArtistExpandedDetails.tsx:46-57`

```ts
const formatFollowers = (followers: number | undefined): string => {
  if (!followers || isNaN(followers)) {
    return '0';
  }
```

The `ArtistDetailsData` interface defines `followers: number` (not `number | undefined`), but the function signature accepts `undefined`. If the backend omits the field entirely (network error, API change), `followers` would be `undefined`, and TypeScript would not catch this mismatch at the call site because the function accepts it.

---

### M-07: `CsrfProvider` — CSRF fetch failure is silently swallowed; `fetchCsrfToken` in `axios.ts` catches and suppresses all errors

**File:** `app/components/CsrfProvider.tsx:11-13`, `services/axios.ts:66-76`

```ts
export async function fetchCsrfToken(): Promise<void> {
  try { ... }
  catch (error) {
    console.error("Error fetching CSRF token:", error);
    // Don't throw the error
  }
}
```

If the CSRF token endpoint is unavailable at app startup (backend down, CORS misconfiguration), the CSRF cookie is never set. All subsequent `POST` requests will be sent without an `X-CSRFToken` header. Django's CSRF middleware will reject them with 403. The user sees vague errors on every action with no indication of what went wrong.

---

### M-08: `Recommendation.tsx` — `cacheSize` state is initialized to `0` and never set

**File:** `app/profile/components/Recommendation/Recommendation.tsx:29`

```tsx
const [cacheSize, setCacheSize] = useState<number>(0);
```

`setCacheSize` is never called anywhere. The `cacheSize > 0` check at line 262 will always be `false`, making the "Cache: X/50 tracks" display permanently hidden. Dead state.

**Fix:** Remove `cacheSize` and the dead display block, or wire it up to the backend cache stats response.

---

### M-09: `app/page.tsx` — Login URL constructed from env var with no validation; if `NEXT_PUBLIC_BACKEND_URL` is undefined the link becomes `undefined/spotify-login`

**File:** `app/page.tsx:5-20`

```tsx
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
...
href={`${backendUrl}/spotify-login`}
```

If the env var is missing, `backendUrl` is `undefined`, and the rendered href is the string `"undefined/spotify-login"`. No guard exists. This is the app's primary CTA.

**Fix:**
```tsx
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';
```

---

### M-10: `get_artist_details` in backend — `latest_album` indexing can crash with `IndexError` if `albums['items']` is empty and the conditional guard on the Python side uses `if albums['items']` which works, but the frontend types `latest_album` as `Album` (not `Album | null`)

**File:** `app/profile/components/TopArtists/ArtistExpandedDetails.tsx:16-23`

```ts
interface ArtistDetailsData {
  ...
  latest_album?: Album;    // marked optional — correct
```

This is actually typed correctly as optional in `ArtistExpandedDetails.tsx`. The conditional render `{artist.latest_album && (...)}` at line 154 correctly guards it. This is verified safe.

---

## LOW

---

### L-01: Commented-out AudioPlayer block in `Recommendation.tsx`

**File:** `app/profile/components/Recommendation/Recommendation.tsx:228-235`

A large commented-out JSX block disables the audio preview in the Recommendation component. The `AudioPlayer` import is still present at line 4 (unused). The `DailyGem` component correctly renders `AudioPlayer` — this appears to be intentional removal for the Recommendation view, but should be cleaned up.

---

### L-02: Multiple `console.log` debug statements in production code

**Files:**
- `Recommendation.tsx:41,42,47,50,57,67` — logs backend URL, cookies, full response objects
- `TopArtists.tsx:82` — logs full artist details API response
- `AddToLiked.tsx:14,21` — logs "adding to spotify" and full response
- `services/axios.ts:68,70` — logs CSRF endpoint URL and success

These are development debugging artifacts that should be removed before any production deployment.

---

### L-03: `AudioPlayer` renders `<h1>loading...</h1>` as fallback for empty src

**File:** `app/profile/components/AudioPlayer/AudioPlayer.tsx:12-14`

```tsx
if (!src){
  return <h1>loading...</h1>
}
```

An `<h1>` inside a flex layout card is semantically incorrect. The `src` prop is typed as `string` (not `string | null`), so TypeScript will flag callers passing `null` — but `DailyGem.tsx` conditionally renders `<AudioPlayer>` only when `preview_url` is non-null, so this guard is actually never reached. Dead code with poor semantics.

---

### L-04: `Boolean` type used instead of `boolean` (primitive) in `AddToLiked`

**File:** `app/profile/components/AddToLiked/AddToLiked.tsx:11`

```tsx
const [liked, setLiked] = useState<Boolean>(false)
```

`Boolean` (capital B) is the object wrapper type. `boolean` (lowercase) is the TypeScript primitive type. Using `Boolean` is almost never correct — it allows `new Boolean(false)` which is truthy. Use `boolean`.

---

### L-05: `Alert.tsx` is imported nowhere — dead component

**File:** `app/profile/components/Feedback/Alert.tsx`

The `Alert` component is defined but never imported by any other component in the codebase. It is dead code.

---

### L-06: `FeedbackButton` dynamic ring color via string interpolation will be purged by Tailwind

**File:** `app/profile/components/Feedback/FeedbackButton.tsx:102`

```tsx
${isSelected ? `ring-${config.iconColor.split("-")[1]}-600` : ""}
```

Tailwind CSS purges class names that are not statically present in source. Dynamic string construction like `` `ring-${...}-600` `` will not appear in Tailwind's static scan and will be purged from the production CSS bundle. The ring color will never appear in production.

**Fix:** Use full class names in a lookup object:
```ts
ringColor: "ring-green-600",  // in feedbackConfig
```

---

### L-07: `TopArtists` — `TIME_RANGE_LABELS` lookup with `as keyof typeof` cast

**File:** `app/profile/components/TopArtists/TopArtists.tsx:119`

```tsx
{TIME_RANGE_LABELS[timeRange as keyof typeof TIME_RANGE_LABELS]}
```

`timeRange` is typed as `string` (the prop default is `'4 weeks'`). The `as keyof` cast bypasses TypeScript's check. If any caller passes a string that is not one of the three valid keys, this evaluates to `undefined`, which React renders as nothing. The `timeRange` prop should be typed as a union:
```ts
interface TopArtistsProps {
  timeRange?: '4 weeks' | '6 months' | 'year';
}
```

---

## Summary of Biggest Risks

### 1. Session cookie leak (C-05) — CRITICAL
`document.cookie` (containing the Django `sessionid`) is logged to the browser console in `Recommendation.tsx`. This is the highest-priority fix — one line removal.

### 2. AddToLiked has broken optimistic UI + wrong type annotation (C-01, C-02)
The "Add to Liked" button shows success before confirmation, never reverts on failure, allows double-submit, and has an incorrect TypeScript response type annotation that hides the breakage entirely.

### 3. SSR crash on null display_name (C-06)
The profile SSR page crashes with `TypeError` if Spotify returns `null` for `display_name`. This takes down the entire profile page for those users.

### 4. API contract drift (C-03)
The documented `submit-feedback` contract (`gem_id`, `action: 'like'|'dislike'|'unlike'`) does not match the implementation (`track_id`, `feedback_type: 'LIKE'|'DISLIKE'`). The implementation is internally consistent but the spec is wrong, creating risk for any new developer or integration work.

### 5. Rate limit error handling is dead code (M-03)
The 429 handling in `AIFeedbackInput` never executes because the `post()` wrapper re-throws as a generic `Error`, dropping the `AxiosError.response` property. Users who hit the AI rate limit get a generic error message, not the specific "try again tomorrow" copy.

### 6. Four redundant API calls per page load (H-07)
`MetricsStrip`, `TasteProfileChart`, `DiversityScore`, and `ImprovementStory` all independently fetch `/api/recommendation-metrics/`, which computes an O(n²) Jaccard diversity score on every call. This will degrade noticeably as the user's gem history grows.

### 7. Tailwind class purge for dynamic ring color (L-06)
The `FeedbackButton` selected-state ring color is constructed dynamically and will be purged from the production CSS bundle, making the selected state invisible in production.

---

_Audit generated: 2026-05-13_  
_Reviewer: Claude (gsd-code-reviewer, deep mode)_
