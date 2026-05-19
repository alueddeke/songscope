# SongScope — ML & Data Science Concepts

This document is a technical reference for every algorithm and technique implemented in SongScope. It is written for an interviewer who wants to go deeper than the Q&A in [INTERVIEW_PREP_SONGSCOPE.md](INTERVIEW_PREP_SONGSCOPE.md) and for an engineer who wants to understand the math behind a specific component. The companion architecture document is [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md).

## Table of Contents

1. [Cosine Similarity](#cosine-similarity)
2. [Novelty Scoring (Bell-Curve)](#novelty-scoring-bell-curve)
3. [Thompson Sampling](#thompson-sampling)
4. [Online Learning (SGD on Taste Vector)](#online-learning-sgd-on-taste-vector)
5. [Jaccard Diversity](#jaccard-diversity)
6. [Recommendation Evaluation Metrics](#recommendation-evaluation-metrics)
7. [Compound Success Metric](#compound-success-metric)
8. [Gem Explanation (Template-Based, Deterministic)](#gem-explanation-template-based-deterministic)
9. [Spotify API Deprecation Pivot](#spotify-api-deprecation-pivot)
10. [Further Reading](#further-reading)

---

## Cosine Similarity

### Intuition

SongScope represents a user's taste as a dictionary of genre counts — how many times each genre appears across the user's top artists. A candidate track is represented similarly: a binary vector over the genres of the track's artist. Cosine similarity measures the angle between these two vectors: if they point in the same direction (same genre mix), the similarity is high; if they are orthogonal (no shared genres), it is zero.

The key advantage over dot product or Euclidean distance is that cosine similarity is scale-invariant. A user who has 100 "indie" observations and another who has 10 both get the same similarity score against an indie track — magnitude doesn't dominate, only direction does. This mirrors how Pandora-style content filtering works: genre proportion, not raw count, is what matters.

### Formula

```
cos(A, B) = (A · B) / (||A|| · ||B||)
```

where `A · B` is the dot product, `||·||` is the L2 norm, and the result is in [0, 1] for non-negative genre count vectors.

### Code (in this codebase)

```python
# Source: backend/apps/recommendations/hybrid_recommendation_engine.py, lines 813-824
def _cosine_similarity(self, vec_a: dict, vec_b: dict) -> float:
    """Cosine similarity between two genre count dicts. Returns 0.0 if either empty."""
    if not vec_a or not vec_b:
        return 0.0
    keys = set(vec_a.keys()) | set(vec_b.keys())
    a = np.array([vec_a.get(k, 0.0) for k in keys])
    b = np.array([vec_b.get(k, 0.0) for k in keys])
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
```

The union of keys from both dicts forms the feature space, so genres present in only one vector contribute zero to the other's component — correctly treated as orthogonal dimensions.

### Interview Talking Point

"Cosine similarity is ideal here because TF-IDF-style genre counts vary wildly between artists — a niche indie artist may have 2 genre tags while a major pop act has 12. Cosine normalizes for that magnitude difference so genre proportion drives similarity, not artist popularity. Same reasoning as Pandora's Music Genome Project: match on musical DNA direction, not quantity."

---

## Novelty Scoring (Bell-Curve)

### Intuition

Most recommendation systems score novelty as `1 - popularity / 100` — a simple linear inverse. This penalizes popular tracks but surfaces extremely obscure ones (popularity near 0). In practice, recommending garage-band tracks the user has never heard of and cannot connect to is not useful discovery; it is noise.

SongScope uses a Gaussian bell-curve centered at a preferred popularity midpoint (default: 30, i.e., moderately underground). Tracks near the midpoint score close to 1.0. Tracks that are either too obscure (popularity 0–5) or too mainstream (popularity 70+) both receive lower scores. This encodes the observation that "hidden gems" sit in a sweet spot — recognizable enough to enjoy, unknown enough to feel like a discovery.

### Formula

```
novelty(pop) = exp( -((pop - midpoint)^2) / (2 * width^2) )
```

Cold-start defaults: `midpoint = 30`, `width = 20`. The score peaks at 1.0 when `pop == midpoint` and decays symmetrically in both directions. The decay radius is controlled by `width` — a larger width produces a flatter curve (more tolerance for popularity variance).

### Code (in this codebase)

```python
# Source: backend/apps/recommendations/hybrid_recommendation_engine.py, lines 841-859
# Bell-curve novelty: read preferred_popularity_range once before the loop.
# Defaults: midpoint=30, width=20 (cold-start / no preference set).
prefs = self.profile.data.get('preferences', {})
pop_range = prefs.get('preferred_popularity_range', {'midpoint': 30, 'width': 20})
midpoint = pop_range.get('midpoint', 30)
width = pop_range.get('width', 20) or 20  # guard against width=0 → ZeroDivisionError

# novelty: Gaussian bell-curve centred at preferred popularity midpoint.
# novelty = exp(-((popularity - midpoint)^2) / (2 * width^2))
# Peaks at 1.0 when popularity == midpoint; decays symmetrically outward.
popularity = rec.get('popularity', 50)
novelty = math.exp(-((popularity - midpoint) ** 2) / (2 * width ** 2))
```

Implementation note: `width` is guarded against zero to prevent ZeroDivisionError on malformed profile data. If user preferences evolve (e.g., they consistently like tracks at popularity 60), `preferred_popularity_range` can be updated to re-center the bell.

### Interview Talking Point

"Bell-curve novelty is unusual — most systems use linear `1 - popularity/100`. We chose the Gaussian because pure inverse-popularity recommends garage-band tracks the user can't enjoy. The bell curve encodes a more realistic model: discovery value peaks at a moderate popularity sweet spot, not at zero. The interviewer follow-up is often 'how do you learn the midpoint?' — the answer is gradient ascent on like-rate with respect to `midpoint`, which is straightforward but deferred to a future phase."

---

## Thompson Sampling

### Intuition

SongScope generates candidates from five distinct sources (playlist mining, artist network, genre search, related artists, contextual). Each source has a different track record for producing songs the user likes. The system needs to balance two goals: exploit the best-performing source and explore the others to discover whether they might outperform.

Thompson Sampling solves this by maintaining a Beta distribution over the win rate of each source. When a source produces a liked track, its success count `s` increments; when it produces a skipped or disliked track, its failure count `f` increments. At recommendation time, a weight is sampled from `Beta(s+1, f+1)` for each source. Sources with more successes produce higher samples on average; sources with high uncertainty (few observations) have wider distributions and occasionally produce high samples — natural exploration.

Cold-start rule: a source with fewer than 3 total observations uses its static default weight rather than a Beta sample, preventing extremely noisy early samples from distorting the selection.

### Formula

```
theta_i ~ Beta(s_i + 1, f_i + 1)   for each source i
weight_i = theta_i / max_j(theta_j)
→ all 5 sources receive a weight in (0, 1]; no single source is selected
```

The `+1` prior on both parameters gives every new source a `Beta(1,1) = Uniform(0,1)` starting distribution — no source is assumed to be better or worse at the start.

### Code (in this codebase)

```python
# Source: backend/apps/recommendations/hybrid_recommendation_engine.py, lines 89-142
def get_recommendation_weights(self) -> dict:
    """
    Thompson Sampling bandit for source weight selection.

    For each of the 5 candidate sources, draw a weight from Beta(s+1, f+1)
    where s = successes (liked tracks from this source) and f = failures
    (disliked/skipped tracks from this source), stored in
    UserProfile.data['source_stats'].

    Cold-start rule: if a source has fewer than COLD_START_THRESHOLD total
    observations (s+f < 3), use the static SOURCE_DEFAULTS weight for that
    source instead of sampling.

    If source_stats is completely empty, return static defaults unchanged.

    Returns a dict with all 5 source keys (normalized to max=1.0 so the best
    source gets a 1.0 multiplier) plus
    a 'bandit_active' sentinel key set to True to signal Phase 3 is wired.
    """
    source_stats = self.profile.data.get('source_stats', {})

    if not source_stats:
        result = {source: 1.0 for source in SOURCE_DEFAULTS}
        result['bandit_active'] = True
        return result

    thetas = {}
    for source, default_weight in SOURCE_DEFAULTS.items():
        stats = source_stats.get(source, {'s': 0, 'f': 0})
        n = stats.get('s', 0) + stats.get('f', 0)
        if n < COLD_START_THRESHOLD:
            thetas[source] = default_weight
        else:
            thetas[source] = random.betavariate(
                stats.get('s', 0) + 1,
                stats.get('f', 0) + 1,
            )

    # Normalize to max=1.0 so the best source gets a 1.0 multiplier.
    # Normalizing to sum=1.0 would make each weight ~0.2, penalizing warm
    # sources relative to the cold-start 1.0 baseline — the bandit would
    # work backwards.
    max_weight = max(thetas.values()) or 1.0
    result = {k: v / max_weight for k, v in thetas.items()}
    result['bandit_active'] = True
    return result
```

### Interview Talking Point

"Thompson Sampling over epsilon-greedy because it is parameter-free — no epsilon tuning required. More importantly, it handles cold-start naturally: every source begins at `Beta(1,1)`, which is uniform, so early exploration is broad and narrows as evidence accumulates. Epsilon-greedy would need a fixed exploration budget; Thompson automatically reduces exploration as the best source becomes clear."

---

## Online Learning (SGD on Taste Vector)

### Intuition

The taste vector is a dictionary mapping genre strings to a float weight representing how strongly the user prefers that genre. When the user likes a track, the weights for that track's genres increase; when the user dislikes a track, the weights decrease. This is stochastic gradient descent on a simple preference function: `L = -sum(taste_vector[g] * signal)`, minimized by updating `taste_vector[g] += lr * signal` per genre.

The key design choice is online (per-feedback) updates rather than batch retraining. In a single-user app, batch retraining would require accumulating enough feedback before any model update — a poor experience. Online updates mean the model reflects the very last feedback, with no retraining pipeline needed. The trade-off is noisier updates per step, acceptable here because the learning rate (`TASTE_VECTOR_LR = 0.1`) is small enough to prevent single-feedback over-correction.

### Formula

```
For each genre g in track.genres:
    taste_vector[g] := taste_vector[g] + lr * signal

where:
    signal = +1  if feedback_type in (LIKE, SAVE)
    signal = -1  if feedback_type in (DISLIKE, SKIP)
    lr = TASTE_VECTOR_LR = 0.1

Dislike update is clamped: taste_vector[g] = max(0.0, taste_vector[g] - lr)
```

### Code (in this codebase)

```python
# Source: backend/apps/recommendations/personalization_engine.py, lines 254-317
def apply_feedback_learning(self, feedback: UserFeedback):
    """
    Update UserProfile.data['taste_vector'] based on new feedback.

    LIKE or SAVE: increment each genre weight by TASTE_VECTOR_LR.
    DISLIKE or SKIP: decrement each genre weight by TASTE_VECTOR_LR, clamped to 0.
    Other feedback types (PLAY, etc.): no taste_vector change.

    Changes persist to DB via profile.save(update_fields=['data']).
    """
    from apps.core.models import UserProfile

    raw_genres = getattr(feedback.track, 'genres', None)
    genres = raw_genres if isinstance(raw_genres, list) else []
    if not genres:
        return

    profile = UserProfile.objects.get(user=self.user)
    taste_vector = profile.data.get('taste_vector', {})

    if feedback.feedback_type in ('LIKE', 'SAVE'):
        for genre in genres:
            taste_vector[genre] = taste_vector.get(genre, 0.0) + TASTE_VECTOR_LR
    elif feedback.feedback_type in ('DISLIKE', 'SKIP'):
        for genre in genres:
            taste_vector[genre] = max(0.0, taste_vector.get(genre, 0.0) - TASTE_VECTOR_LR)
    else:
        return

    profile.data['taste_vector'] = taste_vector
    profile.save(update_fields=['data'])
```

The same function also updates `source_stats` for the Thompson bandit — a like increments `s` for the source that produced the track, a dislike increments `f`.

### Interview Talking Point

"Online learning means the model never needs a batch retrain — every feedback updates the same dict immediately. This aligns with the single-user constraint: there is no population of users to aggregate over, so a batch approach would be waiting for the user to accumulate 100 likes before updating. The learning rate of 0.1 was chosen by intuition; in production you would cross-validate it against held-out like-rate data."

---

## Jaccard Diversity

### Intuition

A good recommendation engine should not repeatedly suggest tracks from the same genre. Jaccard diversity measures how different the engine's recommendations are from each other, using set intersection and union on genre tags.

For any pair of recommended tracks, Jaccard distance is `1 - |A ∩ B| / |A ∪ B|`: 0 means identical genre sets, 1 means completely disjoint. The overall diversity score is the mean pairwise Jaccard distance across all N*(N-1)/2 pairs in the recommendation history. A high diversity score alongside a high like-rate is strong evidence the engine is genuinely exploring the user's taste rather than overfitting to one genre.

**Known limitation:** `Track.genres` is only populated when the user submits explicit feedback (like/dislike). Most historical DailyGem rows have empty genre lists, which means diversity is computed over a sparse subset of recommendations. This under-reports actual diversity and should be disclosed in an interview context.

### Formula

```
J(A, B) = 1 - |A ∩ B| / |A ∪ B|

diversity_score = mean( J(A_i, A_j) )  for all pairs (i, j), i < j
```

### Code (in this codebase)

```python
# Source: backend/apps/core/views.py, lines 389-403
def _jaccard_distance(genres_a: list, genres_b: list) -> float:
    """
    Compute Jaccard distance between two genre lists.

    Jaccard distance = 1 - |A ∩ B| / |A ∪ B|.
    Convention: both empty → 0.0 (identical empty sets, distance zero).
    If union is empty after dedup → 0.0 (guard against ZeroDivisionError).
    """
    a, b = set(genres_a), set(genres_b)
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return 1.0 - len(a & b) / len(union)
```

### Interview Talking Point

"Diversity is a hard metric to interpret in isolation — a random recommender would score 1.0 diversity. We report it alongside acceptance rate so the interviewer sees both signal quality and variety together. The honest disclosure here is that `Track.genres` sparsity means our diversity number under-reports actual genre spread; in production you would backfill genres from the Spotify artist endpoint at DailyGem creation time."

---

## Recommendation Evaluation Metrics

### Intuition

SongScope operates in a single-user, one-recommendation-per-day setting, which limits the statistical power of any evaluation metric. The metrics endpoint (`/api/recommendation-metrics/`) reports four conceptual evaluation dimensions, framed as "what we measure now" alongside "what we would measure with more users or more recommendations per session."

**Precision@k** — what fraction of the top-k recommendations are relevant? In SongScope's single-gem-per-day model, `k=1` always, so `precision@1 = 1` if the gem was liked, else `0`. Across all historical gems: `precision@k = gem_liked / gem_total` (the gem acceptance rate). This is the primary quality signal.

**Serendipity** — a recommendation is serendipitous if it is both novel (the user did not expect it) and relevant (the user liked it). Formally: `serendipity ≈ novelty * relevance`. In the metrics endpoint this is approximated as `hidden_gem_rate` (fraction of all recommended gems with popularity < 40, regardless of whether the user liked them). A more accurate serendipity proxy is `hidden_gem_rate * gem_acceptance_rate`, which combines underground reach with actual user acceptance.

**Diversity** — mean pairwise Jaccard distance across all recommended tracks. Covered in detail in [Jaccard Diversity](#jaccard-diversity).

**Coverage** — what fraction of the available catalog has been recommended? In SongScope: `coverage = unique_tracks_recommended / catalog_size`. The catalog is Spotify's full library; this number is effectively 0 and is not reported. For a portfolio context, coverage is more meaningful in multi-user or playlist-generation settings.

### Formula

```
precision@k      = liked_in_k / k                        (k=1 here → gem_liked / gem_total)
serendipity      ≈ hidden_gem_rate                        (approx: popularity < 40, no was_liked filter)
diversity        = mean pairwise Jaccard (see above)
coverage         = unique_items_recommended / catalog_size
```

### Code (in this codebase)

The `/api/recommendation-metrics/` endpoint in `backend/apps/core/views.py` (lines 406-499) returns these fields:

```
gem_acceptance_rate  → precision@1 aggregate
hidden_gem_rate      → serendipity proxy (popularity < 40, no was_liked filter)
diversity_score      → mean pairwise Jaccard
improvement_story    → first_7_rate vs last_7_rate (learning signal, not an eval metric per se)
```

### Compound Hit Rate

`compound_hit_rate` is a v1.1 addition to the metrics endpoint. It is a broader version of `gem_acceptance_rate` that counts a gem as a "hit" if the user liked it OR saved it to their Spotify library — whichever came first.

**Formula:**

```
compound_hit_rate = compound_hits / gem_total

where compound_hits = count of gems where (was_liked IS True OR was_saved IS True)
```

**Why OR semantics:** A user who saves a gem to Spotify but never taps the in-app thumbs-up has signalled strong value. Restricting the numerator to `was_liked IS True` would under-count positive engagement for users who prefer the Spotify save gesture. Using OR captures both pathways.

**Why `IS True` and not a truthiness check:** Python's `is True` identity check means `None is True` evaluates to `False`. A gem with no feedback recorded yet (`was_liked = None`, `was_saved = None`) is treated as a miss, not a hit. This prevents NULL values from inflating the metric.

Source: `backend/apps/core/views.py`, lines 425-428.

### Interview Talking Point

"These metrics are informative but low-power in a single-user, one-gem-per-day system. The primary signal is `gem_acceptance_rate`. The interesting story is `improvement_story`: if the last-7 like-rate is higher than the first-7, the taste-vector SGD is working. A flat or declining improvement story would indicate the model needs a higher learning rate or more feedback volume."

---

## Compound Success Metric

### Intuition

Each candidate track receives a composite score that weights three independent signals: how well the track's genres align with the user's taste (genre similarity), how novel the track is (neither too obscure nor too mainstream), and whether the track's artist has positive or negative history with the user (feedback multiplier). A Thompson-sampled source weight is then applied as a post-score multiplier.

The three weights (0.4, 0.3, 0.3) are intentionally unequal: genre fit is weighted most heavily because it is the strongest predictor of relevance in a content-based system. Novelty and feedback history are secondary signals. The weights were chosen by design intuition, not learned — a natural follow-up question from an interviewer is "how would you learn these weights?", addressed in the talking point below.

### Formula

```
final_score = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier

post-score:  final_score *= source_weight_i   (Thompson-sampled weight for the track's source)

where:
    genre_sim          = cosine_similarity(candidate_genres, taste_vector)
    novelty            = exp(-((popularity - midpoint)^2) / (2 * width^2))
    feedback_multiplier = 1.5 if artist liked, 0.5 if artist disliked, 1.0 otherwise
```

### Code (in this codebase)

```python
# Source: backend/apps/recommendations/hybrid_recommendation_engine.py, lines 877-882
# LOCKED formula — do not adjust weights
rec['score'] = 0.4 * genre_sim + 0.3 * novelty + 0.3 * feedback_multiplier

# Post-score multiplier: apply Thompson-sampled source weight.
# Unknown source (no key) gets 1.0 — neutral, no boost or penalty.
rec['score'] *= source_weights.get(rec.get('source', ''), 1.0)
```

### Interview Talking Point

"The weights (0.4, 0.3, 0.3) were set by intuition: genre fit should dominate in a content-based system. A follow-up question I would ask myself: 'how would you learn these weights?' The answer is gradient ascent on like-rate as a proxy for user satisfaction — treat the weights as parameters, collect feedback, compute `dL/dw` numerically (or via automatic differentiation if you port the scorer to PyTorch), update. With only one gem per day, you need at least 50–100 feedback events before the gradient estimate is stable."

---

## Gem Explanation (Template-Based, Deterministic)

### Intuition

Each `DailyGem` row has an `explanation` field — a one-sentence human-readable description of why a particular track was chosen. An interviewer reading the codebase might assume this is generated by an LLM (the system does call OpenAI for the `AIFeedback` feature). It is not.

The explanation is produced by `_build_gem_explanation()`, a pure Python function in `backend/apps/core/views.py` (lines 1037–1092). It takes the three score breakdown components (`genre_sim`, `novelty`, `feedback_multiplier`) and the track metadata, finds the dominant scoring component, and fills one of four fixed sentence templates. There is no external call, no randomness, and no AI: the same breakdown always produces the same sentence.

### How It Works

```
source_str = f'via {source}' if source else 'via discovery'
components = {genre_sim, novelty, feedback_multiplier}
dominant = max(components, key=components.get)

# Empty or all-zero breakdown → fallback (early return at start of function)
if not breakdown or all(v == 0.0 for v in components.values()):
    → "Picked based on your listening patterns"

if dominant == 'genre_sim':
    pct = round(genre_sim * 100)
    → f"Matches your listening taste — genre similarity: {pct}%, discovered {source_str}"
elif dominant == 'novelty':
    → f"A hidden gem — low popularity score makes it a genuine discovery, found {source_str}"
else:  # feedback_multiplier
    → f"You've liked {artist_name} before — that feedback boosted this pick, sourced {source_str}"
```

The three sentence shapes are constants; there is no model inference step.

### Why Deterministic by Design

Determinism has two benefits for a portfolio project:

1. **Debuggability.** Given a `score_breakdown` dict and track metadata, you can reproduce the explanation from the DB row without re-running any model.
2. **No external dependency at render time.** If OpenAI is unreachable, gems still get explanations. The `AIFeedback` feature (which does call OpenAI) is a separate code path triggered only when the user explicitly requests AI feedback.

### Code (in this codebase)

```python
# Source: backend/apps/core/views.py, lines 1037-1092
def _build_gem_explanation(breakdown, track_name, artist_name, source) -> str:
    """
    Pure function: no external calls, no logging, no exceptions on any reasonable input.
    Returns one of four sentence shapes based on the dominant scoring component.
    """
    components = {
        'genre_sim': breakdown.get('genre_sim', 0),
        'novelty': breakdown.get('novelty', 0),
        'feedback_multiplier': breakdown.get('feedback_multiplier', 0),
    }
    dominant = max(components, key=components.get)
    # Three fixed sentence templates — no LLM
    ...
```

### Interview Talking Point

"The explanation field looks like it could be AI-generated — it reads as natural language. But it is a pure function: three `if` branches, four sentence templates, deterministic output. I made this choice deliberately. An LLM call at gem-retrieval time would add latency, a billing dependency, and a failure mode. The template approach is instant, free, and reproducible. The honest disclosure is that the sentences are formulaic — a future version could use a fine-tuned model if richer explanations mattered. For a portfolio system the deterministic version is strictly better."

---

## Spotify API Deprecation Pivot

### Intuition

SongScope was originally designed around Spotify's `/v1/audio-features` endpoint, which returned per-track acoustic measurements: BPM (tempo), energy, valence (mood), acousticness, danceability, and instrumentalness. These features were the intended dimensions for content-based filtering — the system would embed each track as a vector in audio-feature space and compute cosine similarity against the user's aggregate profile built from liked tracks.

In late 2024, Spotify deprecated the `/v1/audio-features` endpoint for new developer applications. The endpoint was silently removed from the API surface without a migration path. This broke the foundational design assumption.

**The pivot:** SongScope substituted genre-based cosine similarity and the Gaussian popularity bell-curve — both computable from endpoints that remain active (`/v1/artists/{id}` for genre tags, `popularity` field on `/v1/tracks/{id}`). Genre vectors carry meaningful semantic signal: an "indie dream-pop" artist and a "shoegaze" artist are far more similar to each other than either is to a "latin trap" artist. Popularity as a novelty proxy captures the discovery dimension that valence/energy would have captured for mood.

The consequence is that features that are not derivable from genre tags or popularity — BPM, acoustic texture, vocal style — are invisible to the current recommender. A user who loves fast, energetic music will get the same genre-similarity score as a user who loves slow, atmospheric music in the same genre. This is a known limitation and an honest disclosure for interviews.

### Interview Talking Point

"The Spotify audio-features deprecation is a portfolio-strength story, not a failure story. Every production ML system eventually hits an upstream API or data source change that invalidates a core design assumption. The ability to identify alternative signals that are still available, adapt the architecture, and ship a working system is exactly the engineering judgment that senior roles require. In this case, genre tags and popularity are weaker proxies for musical similarity than acoustic features — but they are real signals, they ship, and the system generates genuine recommendations. The right answer in an interview is to name the limitation honestly and then describe what you would add next: if Last.fm or AcousticBrainz re-expose audio features, the cosine similarity architecture is unchanged — you swap the feature vectors."

---

## Further Reading

- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) — Architecture diagram (Mermaid), component descriptions, API surface, and data flow walkthrough.
- [INTERVIEW_PREP_SONGSCOPE.md](INTERVIEW_PREP_SONGSCOPE.md) — Q&A format interview preparation covering ML design decisions, system trade-offs, and project narrative.
- [.planning/ROADMAP.md](.planning/ROADMAP.md) — Phase-by-phase build history with decisions and verification criteria.
