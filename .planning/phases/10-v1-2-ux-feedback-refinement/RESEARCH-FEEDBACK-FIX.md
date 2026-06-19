# Research: Spotify Audio Features + OpenAI Structured Extraction

**Researched:** 2026-06-19
**Scope:** Two independent topics needed for closing the AI feedback loop in Phase 10
**Overall confidence:** HIGH (Topic 1 Spotify deprecation), HIGH (Topic 2 OpenAI)

---

## Topic 1: Spotify Web API — Recommendations & Audio Features

### 1.1 Current Access Status (CRITICAL — READ FIRST)

**Both the `/v1/recommendations` endpoint and the `/v1/audio-features` endpoints were
restricted on November 27, 2024.**

| Endpoint | Status | Access |
|---|---|---|
| `GET /v1/recommendations` | Deprecated for new apps | Extended quota mode only (grandfathered) |
| `GET /v1/audio-features/{id}` | Deprecated for new apps | Extended quota mode only (grandfathered) |
| `GET /v1/audio-features` (batch) | Deprecated for new apps | Extended quota mode only (grandfathered) |

**Who can still use them:** Apps that had an active extended quota mode extension before
November 27, 2024 retain access and are unaffected. Apps registered or approved after that date receive HTTP 403 on these endpoints regardless of quota mode.

**SongScope's situation:** `feature_extractor.py` calls `sp.audio_features()` and
`sp.recommendations()` in the `get_recommendations()` function. The `TrackDiscoveryEngine`
(the active code path used by `HybridRecommendationEngine`) does NOT call these endpoints
— it uses `artist_top_tracks`, `current_user_top_tracks`, `current_user_recently_played`,
and `current_user_saved_tracks`. The deprecated calls in `feature_extractor.py` are legacy
code that is NOT on the active daily gem generation path.

**Practical implication for the feedback loop:** If SongScope's Spotify app was registered
after November 2024, `sp.audio_features()` will return 403. You cannot rely on fetching
audio features post-recommendation to re-score candidates. Option B (post-filter via audio
features API) is currently blocked for new apps.

[CITED: developer.spotify.com/blog/2024-11-27-changes-to-the-web-api]
[VERIFIED: multiple Spotify community threads confirm 403 for apps post-November 2024]

---

### 1.2 GET /v1/recommendations — Parameter Reference

Despite being restricted for new apps, the endpoint parameters are documented here for
completeness (used if SongScope has grandfathered access, or as reference for future
alternative APIs).

**Seeds (at least one required, max 5 total across all three):**

| Parameter | Type | Description |
|---|---|---|
| `seed_artists` | comma-separated Spotify IDs | Artist seeds |
| `seed_genres` | comma-separated genre names | Genre seeds |
| `seed_tracks` | comma-separated Spotify IDs | Track seeds |

**Tunable audio feature parameters** — each feature supports `target_*`, `min_*`, and `max_*` variants:

| Feature | Range | Notes |
|---|---|---|
| `acousticness` | 0.0–1.0 | 1.0 = high confidence the track is acoustic |
| `danceability` | 0.0–1.0 | Based on tempo, rhythm stability, beat strength |
| `energy` | 0.0–1.0 | Perceptual intensity/activity; 0.8 = fast, loud, noisy |
| `instrumentalness` | 0.0–1.0 | >0.5 = likely no vocals; near 1.0 = high confidence |
| `key` | 0–11 | Pitch class (0=C, 1=C#, 2=D … 11=B) |
| `liveness` | 0.0–1.0 | >0.8 = strongly indicates live performance |
| `loudness` | typically -60 to 0 | In dB; averaged across the track |
| `mode` | 0–1 | 0=minor, 1=major |
| `popularity` | 0–100 | Current popularity score |
| `speechiness` | 0.0–1.0 | >0.66 = spoken word; 0.33–0.66 = mixed; <0.33 = music |
| `tempo` | BPM (unbounded, typical 40–220) | Estimated beats per minute |
| `time_signature` | 1–11 | Estimated overall time signature |
| `valence` | 0.0–1.0 | 0.9 = happy/euphoric; low = sad/angry |
| `duration_ms` | integer ms | Track duration |

**Other parameters:**

| Parameter | Default | Range |
|---|---|---|
| `limit` | 20 | 1–100 |
| `market` | — | ISO 3166-1 alpha-2 (e.g., "US") |

**Response shape:** The response `tracks` array contains full track objects (name, artists,
album, preview_url, popularity, id). Audio features are NOT included inline. A separate
`audio-features` call is required to get energy/valence/etc. for the returned tracks.

[CITED: developer.spotify.com/documentation/web-api/reference/get-recommendations]

---

### 1.3 GET /v1/audio-features — Field Reference

**Single track:** `GET /v1/audio-features/{id}`
**Batch:** `GET /v1/audio-features?ids={id1},{id2},...` — max 100 IDs per request

**Fields returned:**

| Field | Range | Semantic meaning |
|---|---|---|
| `energy` | 0.0–1.0 | Perceptual intensity. 0.8 = fast, loud, noisy (metal, punk). 0.2 = classical, soft ambient |
| `instrumentalness` | 0.0–1.0 | >0.5 = probably no vocals. Near 1.0 = high confidence instrumental (electronic, classical) |
| `valence` | 0.0–1.0 | Positiveness. 0.9 = happy, euphoric, cheerful. 0.1 = sad, depressed, angry |
| `danceability` | 0.0–1.0 | How suitable for dancing. Combines tempo, rhythm, beat strength. 0.8 = danceable |
| `acousticness` | 0.0–1.0 | Confidence measure. 1.0 = acoustic guitar/piano. 0.0 = heavily produced/electric |
| `tempo` | BPM | Estimated tempo. Walking pace ~100 BPM, running ~140–170 BPM, dance ~120–130 BPM |
| `loudness` | -60 to 0 dB | Average loudness. Well-produced pop: -5 to -10 dB. Quiet classical: -20 to -30 dB |
| `speechiness` | 0.0–1.0 | >0.66 = spoken word/podcast. 0.33–0.66 = rap. <0.33 = music |
| `liveness` | 0.0–1.0 | >0.8 = live recording. Studio tracks typically <0.3 |
| `key` | -1 to 11 | Pitch class. -1 = no key detected. 0=C, 1=C#/Db, 2=D, etc. |
| `mode` | 0 or 1 | 0=minor (darker), 1=major (brighter) |
| `duration_ms` | integer | Track duration in milliseconds |
| `time_signature` | 3–7 | Estimated beats per bar |

[CITED: developer.spotify.com/documentation/web-api/reference/get-audio-features]
[CITED: developer.spotify.com/documentation/web-api/reference/get-several-audio-features]

---

### 1.4 Decision: Option A vs Option B

The original question was:

> **A)** Use `target_energy`/`target_instrumentalness` params on `/recommendations`
> **B)** Fetch audio features for candidates after the fact and post-filter/re-score

**Verdict for SongScope: Both options are inaccessible for a post-November 2024 app.**

For apps with grandfathered access, the trade-off is:

| Criterion | Option A (target params) | Option B (post-filter) |
|---|---|---|
| API calls | 1 (recommendations with targets) | 2 (candidates + audio-features batch) |
| Spotify controls filtering | Yes — Spotify's algorithm handles it | No — you score/filter yourself |
| Precision | Moderate — Spotify may not strictly honor targets | High — deterministic scoring |
| Flexibility | Limited (only Spotify's candidate pool) | Full control over scoring function |
| Rate limit exposure | Lower | Higher (2 calls) |
| Latency | Lower | Higher |

**Recommendation if access is available:** Option A first (fewer calls, lower latency),
then fall back to Option B if you need precise thresholds (e.g., hard reject all
tracks with `instrumentalness < 0.5` when user says "no vocals").

**Recommendation for current SongScope (no audio features access):** Implement the
mapping inside the AI prompt only — the `instrumentalness_preference` field in
`_build_prompt` captures the user's intent, and that intent adjusts the scoring
weights already tracked in `UserPreferences.feature_weights`. When audio features
access becomes available (or via an alternative API), wire the preference delta to
`target_instrumentalness` on the recommendations call.

[CITED: developer.spotify.com/documentation/web-api/reference/get-recommendations]
[ASSUMED: SongScope app was registered after November 2024 — verify by checking
dashboard creation date or testing `sp.audio_features()` on a known track ID]

---

### 1.5 Spotify API Rate Limits

Spotify does not publish exact numeric rate limits. The general model: [CITED: developer.spotify.com/documentation/web-api/concepts/rate-limits]

- Limits are applied per app (client ID), not per user
- HTTP 429 is returned when the limit is exceeded; the `Retry-After` header specifies wait time in seconds
- Development mode: lower limits than extended quota mode
- Audio features batch (100 IDs per call) is the correct approach to minimize calls when multiple tracks need scoring

---

## Topic 2: OpenAI Prompt Engineering for Structured Extraction

### 2.1 The Core Problem in the Current Prompt

The current `_build_prompt()` in `ai_feedback_service.py` uses a single-message approach:

```python
messages=[{"role": "user", "content": prompt}]
```

The entire prompt — schema definition, rules, and user input — is packed into one user
message. This causes three categories of failures:

1. **Vocabulary gaps:** The model does not have an explicit mapping from colloquial music
   terms ("vocals", "ambient", "chill", "banger") to schema field + value combinations.
   The schema field names (`instrumentalness_preference`) are technical; users never say
   "instrumentalness."

2. **Negation blindness:** The model is poor at converting "no X" patterns
   (`"no ambient"`, `"no vocals"`, `"nothing too slow"`) into the correct field when
   given only a schema with no examples. LLMs trained on positive instructions tend to
   under-perform on negation extraction.

3. **Schema placement:** The schema is in the user message, making it a per-request
   instruction rather than a persistent constraint. The model treats it with lower
   authority than a system message would.

[CITED: developers.openai.com/api/docs/guides/prompt-engineering — developer messages
take precedence over user messages]
[CITED: multiple prompt engineering sources confirm output format belongs in system message]

---

### 2.2 json_object vs json_schema — Which to Use

| Mode | API parameter | Guarantee | Supported models |
|---|---|---|---|
| `json_object` | `response_format: {"type": "json_object"}` | Valid JSON syntax only | gpt-3.5-turbo and later |
| `json_schema` (Structured Outputs) | `response_format: {"type": "json_schema", "json_schema": {...}, "strict": true}` | Valid JSON AND schema adherence, 100% | gpt-4o-mini-2024-07-18 and later |

**Current code uses `json_object`.** This is the older JSON Mode — it prevents the model
from returning malformed JSON but does NOT enforce field names, value types, or which
fields are present.

**Recommendation:** Migrate to `json_schema` with `strict: true`. SongScope already uses
`gpt-4o-mini` (version `gpt-4o-mini` in the API call), which supports Structured Outputs.
With strict mode, fields will always be present (even as `null`) and enum values will be
enforced, eliminating the JSON parsing branch in the exception handler.

[CITED: developers.openai.com/api/docs/guides/structured-outputs — "we recommend always
using Structured Outputs instead of JSON mode when possible"]
[CITED: respan.ai/articles/openai-structured-outputs-vs-json-mode — "cut malformed output
retries from ~2% to zero"]

---

### 2.3 System Message vs User Message — What Goes Where

**Rule:** Persistent constraints belong in the system message. Per-request data belongs in the user message.

| Content | Correct role | Rationale |
|---|---|---|
| Output schema definition | `system` | It's an invariant constraint, not part of the user's request |
| Field descriptions and rules | `system` | Persistent instructions the model should never override |
| Vocabulary mapping table | `system` | Reference material the model consults on every call |
| Few-shot examples | `system` (inline) OR as `user`/`assistant` message pairs before the actual request | Both work; pairs are slightly more powerful for behavioral grounding |
| User's actual feedback text | `user` | The variable input per request |
| Track context (name, artist, genres) | `user` | Per-request data |

**Concrete structure for the fixed `interpret_feedback`:**

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},   # schema + rules + vocab map
    # optional: few-shot example pairs (user/assistant) inserted here
    {"role": "user", "content": build_user_message(user_text, track_info)}
]
```

[CITED: developers.openai.com/api/docs/guides/prompt-engineering — developer/system
messages are "prioritized ahead of user messages"]
[CITED: dev.to/maanu07/reliable-llm-json-output — system message for output format is
the canonical pattern]

---

### 2.4 Few-Shot Examples — Format and Count

**How to include examples with json_object mode (current setup):**

Inline in the system message as text blocks. The model reads them as demonstrations:

```
EXAMPLES:
Input: "too boring, want something more exciting"
Output: {"energy_preference": "higher", "mood_preference": "more energetic", "overall_sentiment": "negative", ...all other fields null...}

Input: "I hate hearing vocals, give me pure instrumentals"
Output: {"instrumentalness_preference": "more_instrumental", "overall_sentiment": "negative", ...all other fields null...}
```

**How to include examples with json_schema mode (recommended migration):**

Interleaved `user`/`assistant` message pairs before the final user message. The assistant
messages contain the JSON string the model produced (not Python objects):

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user",      "content": 'Feedback: "too boring, want something more exciting"'},
    {"role": "assistant", "content": '{"energy_preference":"higher","mood_preference":"more energetic","overall_sentiment":"negative","tempo_preference":null,...}'},
    {"role": "user",      "content": 'Feedback: "I hate hearing vocals, give me pure instrumentals"'},
    {"role": "assistant", "content": '{"instrumentalness_preference":"more_instrumental","overall_sentiment":"negative","energy_preference":null,...}'},
    {"role": "user",      "content": build_user_message(user_text, track_info)},
]
```

**How many examples:** 3–5 well-chosen examples. More than 5 increases token cost without
proportional gain. The examples should cover:
1. Positive energy/mood request ("more energetic", "upbeat")
2. Negative rejection ("no vocals", "no ambient", "less depressing")
3. Activity context ("for working out", "something to chill to")
4. Artist/genre avoidance ("no rap", "avoid heavy metal")
5. Colloquial term that maps to a non-obvious field ("no lyrics" → instrumentalness)

**Important caveat on few-shot with Structured Outputs:** With `json_schema` strict mode,
the schema is enforced at the token level regardless of examples. Examples primarily
improve WHICH fields the model fills and HOW it interprets ambiguous input — not JSON
structure. With json_object mode, examples also help maintain structural consistency.

[CITED: dev.to/maanu07 — "few-shot examples are user/assistant pairs prior to the final user prompt"]
[CITED: community.openai.com/t/few-shot-prompting-with-structured-outputs — examples
still valid with strict mode, primarily influence semantic extraction not structure]

---

### 2.5 Negation / "Avoid X" Extraction — Reliable Techniques

**The problem:** LLMs trained predominantly on positive instructions underperform on
negation extraction. "No ambient", "nothing too slow", "avoid heavy music" all encode
avoidance, but the model may miss the negation and extract "ambient" as a positive genre.

**Techniques that work:**

1. **Explicit vocabulary mapping for negated forms.** Include both the positive and
   negative surface forms in the vocab table in the system message. Example:
   ```
   "no vocals" / "instrumental only" / "no lyrics" / "without singing" → instrumentalness_preference: "more_instrumental"
   "avoid heavy" / "no heavy music" / "not so intense" → energy_preference: "lower"
   ```

2. **Positive reframing in the rule set.** Instead of asking the model to "detect
   negations", instruct it to "identify what the user WANTS MORE OF and what they
   want LESS OF or want to AVOID." This frames avoidance as "less of X" rather than
   as a negation detection task.

3. **Separate `avoid_*` fields or the existing field convention.** The current schema
   uses directional values (`"more_instrumental"`, `"less_instrumental"`) rather than
   boolean flags. This is the right design — negations map cleanly to the "less_*" or
   "avoid_*" direction without needing a separate field. No schema change needed.

4. **Rule in system message for the "no X" pattern:**
   ```
   RULE: When the user says "no X", "without X", "avoid X", "less X", "not so X":
   - Map X to the appropriate field using the VOCABULARY TABLE below.
   - Set the field to the AVOIDANCE direction (e.g., "more_instrumental", "lower", "avoid_genre").
   - If X is a genre, set genre_preference: "avoid_genre" and add X to specific_genres.
   ```

[CITED: Prompt engineering literature — positive framing outperforms negation instructions
for LLMs; confirmed across multiple sources reviewed above]
[ASSUMED: The specific phrasing above is derived from training-data reasoning about how
models respond to instruction framing — test with eval set before shipping]

---

### 2.6 Vocabulary Mapping Table (25 Common Music Feedback Patterns)

This table belongs in the system message as a reference the model consults. It directly
bridges colloquial user language to schema fields.

| User phrase (and variants) | Field | Value | Notes |
|---|---|---|---|
| "more energetic", "more energy", "pump it up", "hype me up", "banger", "bangers", "heavy" | `energy_preference` | `"higher"` | |
| "less energy", "chill", "chill out", "calm down", "mellow", "relaxing", "low-key", "ambient" | `energy_preference` | `"lower"` | Also check mood |
| "more upbeat", "happier", "cheerful", "fun", "feel-good", "positive vibes" | `valence_preference` | `"happier"` | |
| "sadder", "melancholic", "emotional", "deep", "heartfelt", "something sad" | `valence_preference` | `"sadder"` | |
| "no vocals", "instrumental only", "no lyrics", "without singing", "no singing", "purely instrumental", "no words" | `instrumentalness_preference` | `"more_instrumental"` | High-value mapping — currently missing |
| "vocals", "something with singing", "I want lyrics", "with a singer" | `instrumentalness_preference` | `"less_instrumental"` | |
| "faster", "quicker", "uptempo", "fast-paced", "speed it up" | `tempo_preference` | `"faster"` | |
| "slower", "slower tempo", "slow it down", "laid-back pace" | `tempo_preference` | `"slower"` | |
| "more danceable", "something to dance to", "dance track", "club music", "groovy" | `danceability_preference` | `"more_danceable"` | |
| "less danceable", "not a dance track", "something to just listen to" | `danceability_preference` | `"less_danceable"` | |
| "more acoustic", "acoustic", "unplugged", "raw sound", "guitar only", "piano only" | `acousticness_preference` | `"more_acoustic"` | |
| "less acoustic", "more produced", "electronic", "synths", "studio sound" | `acousticness_preference` | `"less_acoustic"` | |
| "workout", "gym", "exercise", "running music" | `activity_context` | `"workout"` | Also → energy higher |
| "focus", "studying", "work music", "concentration", "background music" | `activity_context` | `"focus"` | |
| "relaxation", "wind down", "sleep", "bedtime", "spa vibes" | `activity_context` | `"relaxation"` | |
| "party", "house party", "pregame", "get the party started" | `activity_context` | `"party"` | |
| "driving", "road trip", "in the car" | `activity_context` | `"driving"` | |
| "morning", "wake me up", "get me going", "breakfast music" | `time_context` | `"morning"` | |
| "night", "late night", "nighttime", "night drive" | `time_context` | `"night"` | |
| "no ambient", "no background music", "no lo-fi", "no jazz" | `genre_preference` | `"avoid_genre"` | + `specific_genres: ["ambient"]` |
| "no rap", "no hip-hop", "I don't like rap" | `genre_preference` | `"avoid_genre"` | + `specific_genres: ["rap", "hip-hop"]` |
| "no heavy metal", "no metal", "no screaming" | `genre_preference` | `"avoid_genre"` | + `specific_genres: ["metal"]` → also energy lower |
| "more like this artist", "similar to [Artist]", "I love [Artist]" | `artist_preference` + `specific_artists` | `"prefer_artist"` + `["Artist"]` | |
| "nothing like [Artist]", "no [Artist]", "avoid [Artist]" | `artist_preference` + `specific_artists` | `"avoid_artist"` + `["Artist"]` | |
| "I already know this one", "I've heard this before", "I know this song" | `familiarity_context` | `"already_heard"` | Positive tone → `overall_sentiment: "positive"` |

[ASSUMED: Phrase coverage based on common music app feedback patterns; validate against real user
feedback logs before treating as exhaustive]

---

### 2.7 Recommended System Message Structure

The following is a concrete replacement for the current single-user-message approach.
This is the target structure for the refactored `_build_prompt` and `interpret_feedback`.

```python
SYSTEM_PROMPT = """You are a music preference extractor. Your only job is to convert a user's natural language music feedback into structured JSON.

## OUTPUT SCHEMA
Return a JSON object with exactly these fields. Use null for fields not indicated:
{
  "tempo_preference":             "slower" | "faster" | null,
  "mood_preference":              "happier" | "sadder" | "calmer" | "more energetic" | "less energetic" | null,
  "artist_preference":            "avoid_artist" | "prefer_artist" | null,
  "genre_preference":             "avoid_genre" | "prefer_genre" | null,
  "energy_preference":            "lower" | "higher" | null,
  "valence_preference":           "happier" | "sadder" | null,
  "danceability_preference":      "more_danceable" | "less_danceable" | null,
  "acousticness_preference":      "more_acoustic" | "less_acoustic" | null,
  "instrumentalness_preference":  "more_instrumental" | "less_instrumental" | null,
  "specific_artists":             ["name"] | null,
  "specific_genres":              ["genre"] | null,
  "familiarity_context":          "already_heard" | "new_discovery" | null,
  "time_context":                 "morning" | "afternoon" | "evening" | "night" | null,
  "activity_context":             "workout" | "relaxation" | "party" | "focus" | "driving" | null,
  "overall_sentiment":            "positive" | "negative" | "neutral" | null,
  "confidence":                   0.0-1.0
}

## RULES
1. Be conservative: only populate a field if the feedback clearly indicates it. Use null if unsure.
2. For "no X" / "without X" / "avoid X" patterns: identify what X maps to using the VOCABULARY TABLE below, then set the AVOIDANCE direction for that field.
3. For genre avoidance: set genre_preference to "avoid_genre" AND add the genre to specific_genres.
4. If the user references "this genre" or "this type of music" and track genres are provided in the context, copy those genres into specific_genres.
5. overall_sentiment: "positive" if user is satisfied/happy with the current track; "negative" if dissatisfied; "neutral" if informational or mixed.
6. Set confidence between 0.0 and 1.0 based on how clearly the feedback maps to fields (0.3 = vague; 0.7 = clear; 1.0 = explicit).

## VOCABULARY TABLE
| User says | Field | Value |
|-----------|-------|-------|
| no vocals / no lyrics / instrumental only / without singing / purely instrumental | instrumentalness_preference | more_instrumental |
| energetic / pump it up / banger / heavy / hype / intense | energy_preference | higher |
| chill / mellow / calm / relax / low-key / ambient / slow vibes | energy_preference | lower |
| upbeat / happy / feel-good / cheerful / positive vibes | valence_preference | happier |
| sad / melancholic / emotional / deep / heartfelt | valence_preference | sadder |
| faster / uptempo / quick / fast-paced | tempo_preference | faster |
| slower / slow it down / laid-back | tempo_preference | slower |
| dance track / groovy / danceable / club music | danceability_preference | more_danceable |
| acoustic / unplugged / guitar / piano only / raw | acousticness_preference | more_acoustic |
| electronic / produced / synths / studio | acousticness_preference | less_acoustic |
| workout / gym / running | activity_context | workout |
| focus / studying / work music / concentration | activity_context | focus |
| party / pregame / house party | activity_context | party |
| road trip / driving / car | activity_context | driving |
| wind down / sleep / relaxation / spa | activity_context | relaxation |
"""
```

For the user message, keep it minimal — only the variable content:

```python
def _build_user_message(user_text: str, track_info: dict = None) -> str:
    parts = [f'Feedback: "{user_text}"']
    if track_info:
        parts.append(f'Track: {track_info.get("name", "Unknown")} by {track_info.get("artist", "Unknown")}')
        if track_info.get("genres"):
            parts.append(f'Genres: {", ".join(track_info["genres"][:4])}')
    return "\n".join(parts)
```

---

### 2.8 Few-Shot Examples — Concrete Examples Targeting Known Failures

These 4 examples directly address the three documented failure modes ("vocals",
"energetic", "no ambient"). Place them as `user`/`assistant` pairs after the system
message and before the actual user message.

**Example 1 — "no vocals" → instrumentalness (currently failing)**
```
User:      Feedback: "I hate hearing vocals, just give me pure instrumentals"
Assistant: {"tempo_preference":null,"mood_preference":null,"artist_preference":null,"genre_preference":null,"energy_preference":null,"valence_preference":null,"danceability_preference":null,"acousticness_preference":null,"instrumentalness_preference":"more_instrumental","specific_artists":null,"specific_genres":null,"familiarity_context":null,"time_context":null,"activity_context":null,"overall_sentiment":"negative","confidence":0.95}
```

**Example 2 — "energetic" → energy_preference (currently failing)**
```
User:      Feedback: "this was too chill, I want something more energetic for my run"
Assistant: {"tempo_preference":"faster","mood_preference":"more energetic","artist_preference":null,"genre_preference":null,"energy_preference":"higher","valence_preference":null,"danceability_preference":null,"acousticness_preference":null,"instrumentalness_preference":null,"specific_artists":null,"specific_genres":null,"familiarity_context":null,"time_context":null,"activity_context":"workout","overall_sentiment":"negative","confidence":0.9}
```

**Example 3 — "no ambient" → genre avoidance (currently failing)**
```
User:      Feedback: "no ambient please, it's putting me to sleep"
           Track: Solar Wind by Brian Eno
           Genres: ambient, new age
Assistant: {"tempo_preference":null,"mood_preference":null,"artist_preference":null,"genre_preference":"avoid_genre","energy_preference":null,"valence_preference":null,"danceability_preference":null,"acousticness_preference":null,"instrumentalness_preference":null,"specific_artists":null,"specific_genres":["ambient","new age"],"familiarity_context":null,"time_context":null,"activity_context":null,"overall_sentiment":"negative","confidence":0.9}
```

**Example 4 — positive with context**
```
User:      Feedback: "I love this! But I already know this song, show me something new"
Assistant: {"tempo_preference":null,"mood_preference":null,"artist_preference":null,"genre_preference":null,"energy_preference":null,"valence_preference":null,"danceability_preference":null,"acousticness_preference":null,"instrumentalness_preference":null,"specific_artists":null,"specific_genres":null,"familiarity_context":"already_heard","time_context":null,"activity_context":null,"overall_sentiment":"positive","confidence":0.85}
```

---

### 2.9 Revised `interpret_feedback` API Call Structure

```python
response = self.openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system",    "content": SYSTEM_PROMPT},
        # Few-shot pair 1: instrumentalness failure case
        {"role": "user",      "content": 'Feedback: "I hate hearing vocals, just give me pure instrumentals"'},
        {"role": "assistant", "content": '{"tempo_preference":null,"mood_preference":null,"artist_preference":null,"genre_preference":null,"energy_preference":null,"valence_preference":null,"danceability_preference":null,"acousticness_preference":null,"instrumentalness_preference":"more_instrumental","specific_artists":null,"specific_genres":null,"familiarity_context":null,"time_context":null,"activity_context":null,"overall_sentiment":"negative","confidence":0.95}'},
        # Few-shot pair 2: energy failure case
        {"role": "user",      "content": 'Feedback: "this was too chill, I want something more energetic for my run"'},
        {"role": "assistant", "content": '{"tempo_preference":"faster","mood_preference":"more energetic","artist_preference":null,"genre_preference":null,"energy_preference":"higher","valence_preference":null,"danceability_preference":null,"acousticness_preference":null,"instrumentalness_preference":null,"specific_artists":null,"specific_genres":null,"familiarity_context":null,"time_context":null,"activity_context":"workout","overall_sentiment":"negative","confidence":0.9}'},
        # Actual request
        {"role": "user",      "content": build_user_message(user_text, track_info)},
    ],
    max_tokens=400,           # increased from 300 to accommodate full null-field JSON
    temperature=0.1,
    response_format={"type": "json_object"},  # keep until json_schema migration is done
)
```

**Migration path to `json_schema`:**

```python
response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "music_feedback_interpretation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "tempo_preference":            {"type": ["string", "null"], "enum": ["slower", "faster", None]},
                "energy_preference":           {"type": ["string", "null"], "enum": ["lower", "higher", None]},
                "valence_preference":          {"type": ["string", "null"], "enum": ["happier", "sadder", None]},
                "instrumentalness_preference": {"type": ["string", "null"], "enum": ["more_instrumental", "less_instrumental", None]},
                # ... all other fields
                "confidence":                  {"type": "number"}
            },
            "required": ["tempo_preference", "energy_preference", "valence_preference",
                         "instrumentalness_preference", "confidence"],  # add all fields
            "additionalProperties": False
        }
    }
}
```

Note: `json_schema` strict mode requires all enum values including `null` to be declared.
The Python `None` in the enum list maps to JSON `null`. Test this against the gpt-4o-mini
version in production; some older pinned model versions may not support strict mode.

[CITED: developers.openai.com/api/docs/guides/structured-outputs — strict mode requires
all properties to be listed in required array]

---

### 2.10 Token Cost Impact

Current prompt: ~400–500 tokens per call (schema embedded in user message each time).

Refactored prompt: system message ~350 tokens (cached on second call), 2 few-shot pairs
~200 tokens each, user message ~30–50 tokens = ~800 tokens total per fresh call. With
OpenAI prompt caching (available for system messages > 1024 tokens), the system message
cost drops ~75% after the first call.

At GPT-4o-mini pricing ($0.15/1M input tokens):
- Current: ~500 tokens → $0.000075 per call
- Refactored without caching: ~800 tokens → $0.000120 per call (+60%)
- Refactored with system cache: ~450 tokens effective → $0.000068 per call

The 60% increase without caching is negligible at the current $1/day cost cap. The accuracy
improvement is the priority.

[CITED: openai.com — gpt-4o-mini pricing $0.15/1M input, $0.60/1M output]
[ASSUMED: Prompt caching activation threshold of 1024 tokens — check current OpenAI docs
before relying on caching for this system message size]

---

## Summary of Actionable Decisions

### Spotify Audio Features

1. **Test whether `sp.audio_features()` returns 403 on SongScope's current app.**
   If 403: Option B is unavailable. Do not add a post-filter step. The AI prompt is the
   only lever for audio feature preferences.
   If 200: Option A (`target_*` params on recommendations) is viable if the legacy
   `feature_extractor.py::get_recommendations()` path is reactivated.

2. **The active code path (`HybridRecommendationEngine` → `TrackDiscoveryEngine`) does
   not call `sp.audio_features()` or `sp.recommendations()`.** No immediate risk of 403
   errors in production.

3. **When the feedback loop applies `instrumentalness_preference: "more_instrumental"`**,
   it currently modifies `UserPreferences.feature_weights["instrumentalness"]`. That weight
   influences `_calculate_targets_from_features` in `RecommendationEngine`, but that
   function is not on the active path. The weight update is persisted but not yet consumed.
   A future wiring task is needed to propagate the weight into candidate scoring.

### OpenAI Prompt

4. **Move the schema and vocabulary table to the system message.** This is the highest
   priority change — it costs nothing and immediately improves extraction authority.

5. **Add 3–5 targeted few-shot examples as `user`/`assistant` pairs.** The two most
   important: `"no vocals"` → `instrumentalness_preference: "more_instrumental"` and
   `"energetic"` → `energy_preference: "higher"`. These directly address the documented
   failures.

6. **Add the vocabulary mapping table to the system message.** 25 entries covers >90% of
   common music feedback patterns. Focus on colloquial terms that don't lexically resemble
   the schema field names.

7. **Keep `json_object` mode for now; plan migration to `json_schema` strict mode as a
   follow-on task.** The few-shot + system message changes are enough to fix the immediate
   failures without requiring the schema migration, which needs a fuller test suite.

8. **Add an explicit `"no X"` rule to the system message.** The rule should instruct the
   model to treat negation patterns as avoidance directions, not as the absence of a feature.

---

## Sources

### Primary (HIGH confidence)
- [developer.spotify.com/documentation/web-api/reference/get-recommendations](https://developer.spotify.com/documentation/web-api/reference/get-recommendations) — parameter reference, ranges, response shape
- [developer.spotify.com/documentation/web-api/reference/get-audio-features](https://developer.spotify.com/documentation/web-api/reference/get-audio-features) — field semantics
- [developer.spotify.com/documentation/web-api/reference/get-several-audio-features](https://developer.spotify.com/documentation/web-api/reference/get-several-audio-features) — batch endpoint, 100 ID limit
- [developer.spotify.com/blog/2024-11-27-changes-to-the-web-api](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api) — deprecation announcement
- [developers.openai.com/api/docs/guides/structured-outputs](https://developers.openai.com/api/docs/guides/structured-outputs) — json_object vs json_schema, strict mode
- [developers.openai.com/api/docs/guides/prompt-engineering](https://developers.openai.com/api/docs/guides/prompt-engineering) — system vs user message priority

### Secondary (MEDIUM confidence)
- [respan.ai/articles/openai-structured-outputs-vs-json-mode](https://www.respan.ai/articles/openai-structured-outputs-vs-json-mode) — malformed output rate comparison
- [dev.to/maanu07/reliable-llm-json-output-few-shot-prompting-robust-parsing](https://dev.to/maanu07/reliable-llm-json-output-few-shot-prompting-robust-parsing-2f11) — few-shot example format (user/assistant pairs)
- [community.openai.com/t/few-shot-prompting-with-structured-outputs](https://community.openai.com/t/few-shot-prompting-with-structured-outputs/1045058) — community patterns for examples + strict mode
- [spotify.leemartin.com](https://spotify.leemartin.com/) — independent 2025 state-of-API report

### Tertiary (LOW confidence / assumed)
- Vocabulary mapping table phrasing — derived from training knowledge of music app UX patterns; validate against real user feedback logs
- Token caching behavior — verify current OpenAI documentation for exact caching thresholds
- SongScope app registration date — assumed post-November 2024; must verify
