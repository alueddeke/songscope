# SongScope Interview Preparation Guide
## Connecting Your Project to Portable Intelligence's Mission

---

## Executive Summary: Your Journey from Supervised ML to Hybrid Recommendation Systems

**The Original Problem (Data Science Project):**
- Used XGBoost (supervised learning) to predict if songs would be "hits" (popularity > 70)
- Trained on Spotify audio features: energy, tempo, loudness, danceability, valence, acousticness, instrumentalness
- Dataset: 114,000+ songs with 20+ features per song
- Model Performance: 91% accuracy, but only 39% F1-score (struggled with class imbalance)
- **Key Finding**: Genre was overbalanced - when removed, instrumentalness and acousticness became most predictive

**The Pivot (When Spotify Changed):**
Spotify's audio features API **still exists** and works! However, you had to pivot your **recommendation strategy** because:
1. Spotify's `/recommendations` endpoint became unreliable/restrictive
2. Needed a more sophisticated system that learns from **user behavior**, not just audio features
3. Wanted to incorporate **natural language feedback** via AI

**Current Implementation - Hybrid Recommendation Engine:**
Instead of predicting "hits" in isolation, you built a **personalized discovery system** that:
1. **Learns from user behavior** (playlists, listening patterns, feedback)
2. **Adapts recommendation weights** based on feature variance in listening habits
3. **Combines multiple data sources** (collaborative filtering concept without explicit user-user comparison)
4. **Interprets natural language feedback** using OpenAI to adjust preferences
5. **Respects real-world constraints** (API rate limits, cost budgets, error handling)

---

## Technical Deep Dive: How Your System Works

### Architecture Overview

```
User → Spotify OAuth → Django Backend (Python)
                            ↓
                    Hybrid Recommendation Engine
                    /        |         \
              Playlist   Artist    Contextual
               Mining   Network    Analysis
                    \        |         /
                         Scoring
                            ↓
                    Filter & Personalize
                    (Feature Extractor)
                            ↓
                    AI Feedback Loop
                    (OpenAI GPT-4o-mini)
                            ↓
                    Next.js Frontend (React/TypeScript)
```

### 1. The Hybrid Recommendation Engine (Core Innovation)

**Location**: `apps/recommendations/hybrid_recommendation_engine.py`

**Five Parallel Strategies** (Line 58-66):
```python
'recommendation_weights': {
    'playlist_mining': 0.3,      # Find hidden gems in user playlists
    'artist_network': 0.25,      # Explore similar artists
    'contextual': 0.2,           # Time-of-day patterns
    'popularity': 0.15,          # Balance discovery with familiarity
    'feedback': 0.1              # Learn from likes/dislikes
}
```

**Strategy 1: Playlist Mining** (Lines 364-416)
- Mines tracks from user's Spotify playlists
- Filters out already-saved tracks
- **Use Case**: User has a "Workout" playlist → Recommends similar high-energy tracks they haven't saved yet

**Strategy 2: Artist Network** (Lines 418-472)
- Gets top tracks from artists the user already likes
- Avoids disliked artists
- **Use Case**: User likes "Tame Impala" → Explores their deep cuts and B-sides

**Strategy 3: Contextual Recommendations** (Lines 474-552)
- Analyzes listening patterns by time of day (morning/afternoon/evening/night)
- Recommends tracks that match current time context
- **Use Case**: User listens to chill music at night → Recommends acoustic tracks in evening hours

**Why This Matters for Portable Intelligence**:
- **Pattern Recognition**: Like their AI slotting that analyzes pick times to optimize warehouse layout
- **Adaptive Learning**: Weights adjust based on user behavior (similar to predictive task assignment in TED)
- **Resource Optimization**: Respects API rate limits and costs (real-world constraints)

---

### 2. Feature Extraction & Adaptive Weights

**Location**: `apps/recommendations/feature_extractor.py`

**Base Weights from Your Original XGBoost Model** (Lines 10-22):
```python
BASE_WEIGHTS = {
    'acousticness': 0.103040,      # Highest importance
    'instrumentalness': 0.0898047,  # Second highest
    'energy': 0.0886158,`
    'valence': 0.0863662,
    'danceability': 0.08025012,
    # ... etc
}
```

**Adaptive Weight Calculation** (Lines 91-119):
Instead of using fixed weights, your system:
1. **Calculates variance** in user's listening patterns for each feature
2. **Inverse variance weighting**: Features with low variance (consistent preference) get higher weights
3. **Blends with base weights**: `0.7 * adaptive + 0.3 * base` to prevent over-fitting

**Example**:
- User consistently listens to high-energy music (low variance in energy feature)
- System increases energy weight in recommendations
- But maintains some base weight to allow discovery

**The Math** (Line 100-113):
```python
inverse_variances = {feature: 1 / (variance + 1e-6) for feature, variance in variances.items()}
adaptive_weights = {feature: weight / total_weight for feature, weight in inverse_variances.items()}
final_weights = (0.7 * adaptive) + (0.3 * BASE_WEIGHTS)
```

**Why This Matters**:
- **Predictive Analytics**: Like their warehouse optimization that forecasts demand patterns
- **Real-time Adaptation**: System evolves with user behavior
- **Balances Exploration vs Exploitation**: Doesn't get stuck in a bubble

---

### 3. AI Feedback Interpretation

**Location**: `apps/ai/ai_feedback_service.py`

**The Problem**: Users don't just like/dislike songs - they have nuanced preferences:
- "Too slow for working out"
- "Love the guitar but the vocals are weird"
- "Reminds me of my breakup, not now"

**Your Solution**: Natural Language Processing with OpenAI GPT-4o-mini

**Cost & Rate Limiting** (Lines 18-59):
```python
max_requests_per_minute = 50
max_daily_cost = $1.00
cost_per_request = (tokens / 1M) * $0.15
```

**How It Works**:
1. User submits text feedback: "Too fast, prefer slower tempo"
2. OpenAI interprets → `{'tempo_preference': 'slower', 'confidence': 0.85}`
3. System updates weights: Decreases tempo targets for future recommendations
4. Stored in user profile for persistent learning

**Why This Matters for Portable Intelligence**:
- **Natural Interface**: Workers don't need technical training (like their TED system)
- **Cost-Aware**: Production-ready with budget constraints
- **Feedback Loop**: Continuous improvement from real-world usage

---

### 4. The Filtering System (Discovery vs Familiarity)

**Location**: `apps/recommendations/hybrid_recommendation_engine.py` (Lines 631-747)

**The Challenge**: Don't recommend songs users already know!

**Your Multi-Stage Filter**:

**Stage 1**: Check Spotify Liked Songs (Line 670)
```python
saved_status = sp.current_user_saved_tracks_contains(track_ids)
```
- Batch checks (20 tracks at a time) to respect API limits
- Filters out user's liked songs

**Stage 2**: Filter Top Artists (Line 704)
```python
if rec['artist'] in top_artist_names:
    filter_reason = "Top artist - user already knows them"
```
- Users know their top artists well
- System prioritizes discovering **new** artists

**Stage 3**: Recently Played Filter (Lines 749-775)
- Avoids recommending recently played tracks
- Keeps recommendations fresh

**Logging Example** (Lines 701, 714):
```python
logger.info(f"🚫 FILTERED OUT LIKED SONG: {rec['name']} by {rec['artist']}")
logger.info(f"✅ KEEPING TRACK: {rec['name']} by {rec['artist']}")
```

**Why This Matters**:
- **User Experience**: No "I already know this song" frustration
- **Production Logging**: Debugging and monitoring (critical for enterprise software)
- **Graceful Degradation**: If API fails, falls back to cached data

---

### 5. Real-World Production Concerns

**Rate Limiting** (apps/spotify/utils.py referenced in code):
```python
def _check_rate_limit(self) -> bool:
    return self.rate_limit_monitor.check_rate_limit()
```
- Spotify API has strict rate limits
- System checks before each API call
- Prevents 429 errors and IP bans

**Caching Strategy** (Line 84-88):
```python
cached_recommendations = self.profile.get_from_cache(limit)
if cached_recommendations:
    logger.info(f"Returning {len(cached_recommendations)} from cache")
    return cached_recommendations
```
- Reduces API calls
- Improves response time
- TTL: 5 minutes

**Error Handling** (Line 200-203):
```python
except Exception as e:
    logger.error(f"Error in hybrid recommendations: {str(e)}")
    return self._get_fallback_recommendations(limit)
```
- Never returns empty results
- Fallback to simpler discovery engine
- User always gets recommendations

**User Profile Persistence** (apps/core/models.py):
- PostgreSQL/SQLite database
- Stores learned preferences
- Updates daily or on-demand

---

## Connecting to Portable Intelligence's Tech Stack

### How Your Skills Map to Their Needs

| **Their Need** | **Your Experience** | **Evidence in SongScope** |
|---|---|---|
| **Prepare data for ML** | Cleaned 114k song dataset, handled missing values, normalized features | `DataScience_FinalProject_Spotify.ipynb` lines 3fefb191 |
| **Design database schemas** | Django ORM models for users, tracks, feedback, preferences | `apps/core/models.py` |
| **Write REST APIs** | Django REST Framework, 30+ endpoints, pagination | `apps/core/views.py`, `config/settings.py` lines 45-54 |
| **Implement ML models** | XGBoost for classification, adaptive weight algorithms | `feature_extractor.py` lines 91-119 |
| **Frontend development** | Next.js 14, React, TypeScript, Tailwind CSS | `frontend/app/` |
| **Testing own code** | Error handling, logging, fallback strategies | Throughout codebase |
| **Collaborate** | Integrated multiple APIs (Spotify, OpenAI), clear documentation | API integration in views.py |

---

## Practice Interview Questions & Talking Points

### **Question 1: "Walk me through how SongScope works from a technical perspective."**

**Your Answer Structure** (2-3 minutes):

"SongScope is a full-stack music recommendation system I built that learns from user behavior to suggest songs they'll actually enjoy.

**The Core Challenge:** Initially, I used supervised learning - XGBoost - to predict hit songs based on audio features like energy, tempo, and valence. I had 114,000 songs and achieved 91% accuracy. But I realized predicting 'hits' in general isn't as valuable as personalizing recommendations for each user.

**The Pivot:** I built a hybrid recommendation engine that combines five strategies:
1. **Playlist Mining** - discovers hidden gems in their existing playlists
2. **Artist Network** - explores similar artists they might like
3. **Contextual Analysis** - learns their listening patterns by time of day
4. **Popularity Balancing** - balances discovery with familiarity
5. **Feedback Learning** - adapts from user likes/dislikes

**The Technical Stack:**
- **Backend**: Django with Django REST Framework, exposing 30+ API endpoints
- **Frontend**: Next.js 14 with React and TypeScript
- **ML Components**: Feature extraction with adaptive weighting based on variance analysis
- **AI Integration**: OpenAI GPT-4o-mini interprets natural language feedback
- **Database**: SQLite for development (designed for PostgreSQL in production)
- **APIs**: Spotify Web API for user data, OAuth 2.0 for authentication

**Production Considerations:**
- Rate limiting to respect Spotify API constraints
- Caching layer to reduce API calls and improve response time
- Cost budgets on OpenAI usage ($1/day limit)
- Comprehensive logging for debugging
- Fallback strategies for graceful degradation

**The Result**: Users get personalized recommendations that actually introduce them to new music they'll like, not just popular songs they already know."

**Why This Answer Works**:
- Shows problem-solving evolution
- Demonstrates technical breadth (full-stack + ML + AI)
- Highlights production concerns (rate limits, costs, error handling)
- Connects supervised learning (XGBoost) to recommendation systems

---

### **Question 2: "You mentioned starting with XGBoost to predict hits. What did you learn from that model?"**

**Your Answer** (1-2 minutes):

"The XGBoost model was really educational. I trained it on audio features to predict if a song would be a 'hit' - popularity score above 70.

**Key Findings:**
1. **Genre was overbalanced** - it dominated predictions. When I removed genre features, **acousticness and instrumentalness** became the most predictive features, not energy or danceability like I initially hypothesized.

2. **Class imbalance challenges** - I had far more non-hits than hits. Even with 91% accuracy, my F1-score was only 39% because the model struggled to correctly identify hits. I used `scale_pos_weight` in XGBoost to handle this.

3. **Hyperparameter tuning impact** - I used GridSearchCV with cross-validation to find optimal parameters. The best model used:
   - `n_estimators`: 300
   - `max_depth`: 7
   - `learning_rate`: 0.2

This took significant compute time (729 models evaluated), which taught me about the trade-offs between model performance and computational cost.

**What I Applied to SongScope:**
The feature importance weights from XGBoost became my **base weights** in the recommendation system. But instead of predicting hits generally, I calculate **adaptive weights** based on each user's listening variance. If a user has consistent energy preferences (low variance), the system weights energy more heavily for their recommendations.

**The Bigger Lesson:** Supervised learning is powerful for labeled data, but recommendation systems need unsupervised and semi-supervised techniques that learn from implicit feedback (plays, skips, saves) rather than explicit labels."

**Why This Answer Works**:
- Shows understanding of ML fundamentals (class imbalance, hyperparameter tuning, overfitting)
- Demonstrates ability to extract insights from model results
- Shows how you evolved from classification to recommendation systems
- Mentions real-world constraints (compute time, cost)

---

### **Question 3: "How does your system balance discovery with familiarity? Users want new music but not *too* different."**

**Your Answer** (1-2 minutes):

"This is actually one of the most interesting challenges! I call it the **exploration vs exploitation tradeoff**.

**My Multi-Layer Approach:**

**1. Adaptive Feature Weighting (70% adaptive, 30% base)**
```python
final_weights = (0.7 * adaptive_from_user_data) + (0.3 * base_weights_from_xgboost)
```
This prevents the system from getting stuck in a bubble. Even if a user only listens to high-energy music, we maintain some baseline diversity.

**2. Multiple Recommendation Sources**
- **Familiar Territory**: Playlist mining (30% weight) - recommends from their existing playlists
- **Adjacent Discovery**: Artist network (25% weight) - explores artists similar to their favorites
- **Safe Bets**: Popularity balancing (15% weight) - includes some well-known tracks
- **Adventurous**: Contextual analysis (20% weight) - tries new patterns based on time/mood

**3. Smart Filtering**
The system actively **filters out**:
- Songs they've already liked on Spotify
- Tracks from their top artists (they know these artists well)
- Recently played songs

But it **keeps**:
- Lesser-known tracks from genres they like
- New artists with similar sound profiles
- Contextually appropriate music they haven't heard

**4. Feedback Loop**
When users dislike a recommendation, the system:
- Reduces weight for that artist/genre
- Learns from natural language feedback (via OpenAI)
- Adjusts future recommendations

**Real Example:**
If a user loves indie rock but has never explored folk music, the system might recommend a folk track with high energy and guitar (features they like), easing them into a new genre without being jarring.

**Why This Matters for Your Company:**
This is exactly like **AI slotting** in your warehouse optimization - you're balancing **predictability** (efficient pick paths) with **flexibility** (adapting to seasonal changes). Both systems need to learn patterns while avoiding over-optimization that ignores new information."

**Why This Answer Works**:
- Demonstrates deep understanding of recommendation system challenges
- Shows quantitative thinking (specific percentages, weights)
- Connects to their business (warehouse optimization analogy)
- Includes code example (shows you actually implemented this)

---

### **Question 4: "You integrated OpenAI for feedback interpretation. Why use AI instead of simple buttons?"**

**Your Answer** (1-2 minutes):

"Great question! I started with simple like/dislike buttons, but realized users have **much more nuanced preferences**.

**The Problem with Binary Feedback:**
- User dislikes a song - but why?
  - Is it too slow?
  - Wrong genre?
  - Bad vocals but good instrumentals?
  - Right song, wrong mood?

A dislike button captures *that* they didn't like it, but not *why*.

**The AI Solution:**
Users can type natural language feedback like:
- 'Too fast, I prefer slower songs when I'm studying'
- 'Love the guitar but hate the vocals'
- 'Not in the mood for this vibe right now'

OpenAI GPT-4o-mini interprets this and returns structured data:
```json
{
  'tempo_preference': 'slower',
  'context': 'studying',
  'confidence': 0.85
}
```

**The System Then:**
1. Adjusts tempo targets for future recommendations
2. Tags 'studying' as a context preference
3. Stores this in the user profile persistently

**Production Considerations:**
- **Cost Control**: $1/day budget, tracks spend per request
- **Rate Limiting**: 50 requests/minute max
- **Fallback**: If OpenAI fails, falls back to simple like/dislike
- **Token Optimization**: Costs $0.15 per 1M tokens (GPT-4o-mini is cheap)

**Why This Matters:**
It's the same principle as **natural language interfaces in your TED system** - workers don't need technical training to provide useful feedback. The AI bridges the gap between human language and machine-actionable data.

**The Result**: Richer user data leads to better recommendations with minimal user friction."

**Why This Answer Works**:
- Shows you understand UX design (reduce friction)
- Demonstrates cost awareness (production-ready thinking)
- Includes technical details (JSON structure, token costs)
- Connects to their product (TED natural interface)

---

### **Question 5: "How did you handle the Spotify API limitations and rate limits?"**

**Your Answer** (1-2 minutes):

"API integration is never as simple as the docs make it seem! I ran into several challenges:

**Challenge 1: Rate Limiting**
Spotify has strict rate limits - too many requests = 429 errors and potential IP ban.

**My Solution:**
```python
def _check_rate_limit(self) -> bool:
    return self.rate_limit_monitor.check_rate_limit()
```
Before every API call, I check if we're approaching limits. If so, the system:
- Uses cached data instead
- Falls back to simpler recommendation strategies
- Logs the limitation for monitoring

**Challenge 2: OAuth Token Management**
Access tokens expire after 1 hour, refresh tokens can become invalid.

**My Solution:**
- Store tokens in database with expiration timestamps
- Check `is_expired()` before each request
- Automatically refresh tokens when needed
- Graceful degradation if refresh fails (redirect to re-auth)

**Challenge 3: Recommendations API Reliability**
Spotify's `/recommendations` endpoint became unreliable, sometimes returning empty results.

**My Solution - Hybrid Engine:**
Instead of relying on one API endpoint, I built a system that:
1. Mines user's existing data (playlists, top tracks, recent plays)
2. Constructs recommendations from their listening history
3. Uses multiple Spotify endpoints (playlist tracks, artist top tracks, user data)
4. Falls back gracefully if any single endpoint fails

**Challenge 4: API Costs**
While Spotify is free, OpenAI costs money.

**My Solution:**
- Track daily spending: `$1/day limit`
- Log every request cost: `(tokens / 1M) * $0.15`
- Raise exception if budget exceeded
- Monitoring dashboard could track usage over time

**The Production Mindset:**
This is how I approach **all** external dependencies:
- Never trust external APIs to always work
- Always have a fallback strategy
- Monitor usage and costs
- Log everything for debugging

**Why This Matters:**
Your TED system integrates with multiple ERP systems (CSI/SyteLink, Microsoft Business Central). You need developers who understand that integration points are failure points, and plan accordingly."

**Why This Answer Works**:
- Shows defensive programming mindset
- Demonstrates production experience (not just toy projects)
- Includes specific code examples
- Connects to their multi-ERP integration challenges

---

### **Question 6: "Tell me about a bug or challenge you faced in SongScope and how you debugged it."**

**Your Answer** (Use the OAuth issue from today!):

"Just today actually, I was preparing for this interview and wanted to test the live system. I ran into a perfect example of a production debugging scenario.

**The Bug:**
When users clicked 'Login with Spotify,' they'd get a 400 error: `redirect_uri: Insecure`.

**Initial Hypothesis:**
I thought it was an environment variable issue with `OAUTHLIB_INSECURE_TRANSPORT`.

**Debugging Process:**

**Step 1: Check Environment Variables**
```bash
echo $OAUTHLIB_INSECURE_TRANSPORT  # Was set correctly
```

**Step 2: Check Django Settings**
- Verified `ALLOWED_HOSTS` included both `localhost` and `127.0.0.1`
- CORS settings looked correct

**Step 3: Research the Error**
Searched Spotify's documentation and found: **Spotify changed their policy in 2025** - they no longer accept `localhost` in redirect URIs, only loopback IP addresses like `127.0.0.1`.

**Step 4: System-Wide Fix**
Had to update **multiple** files:
- Backend `.env`: `SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/spotify/callback/`
- Frontend `.env.local`: `NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000`
- Django `settings.py`: Add `127.0.0.1:3000` to CORS and CSRF trusted origins
- Spotify Developer Dashboard: Add `127.0.0.1` redirect URI

**Step 5: Restart Services**
- Killed zombie processes on port 8000
- Restarted Django backend (picks up new .env)
- Restarted Next.js frontend (picks up new .env.local)

**The Hidden Issue:**
Even after fixing the backend, the frontend still redirected to `localhost` instead of `127.0.0.1` after successful auth.

**Root Cause:** Backend's `FRONTEND_URL` environment variable was still set to `localhost:3000`.

**Final Fix:**
Updated `FRONTEND_URL=http://127.0.0.1:3000` in backend `.env`, restarted server.

**What I Learned:**
1. **Environment configuration is system-wide** - one variable in the wrong place breaks everything
2. **External API policies change** - always check docs when something breaks
3. **Comprehensive logging helps** - I had logs showing exactly which URL was being used
4. **Test the full flow** - backend and frontend need to be in sync

**Why This Matters:**
In your warehouse systems, you're integrating with multiple ERPs and tracking systems. Configuration management and debugging distributed systems is a daily reality. This experience shows I can methodically track down issues across multiple services."

**Why This Answer Works**:
- Real, recent example (authentic)
- Shows systematic debugging process
- Demonstrates persistence (multiple attempts)
- Shows learning from external changes (API policy updates)
- Connects to their distributed systems environment

---

### **Question 7: "If you had more time, what would you add to SongScope?"**

**Your Answer** (Shows forward thinking):

"Great question! I have a whole roadmap. Here are my top priorities:

**1. Automated Testing**
Right now I'm testing manually. I'd add:
- **Unit tests** for recommendation engine logic (pytest)
- **Integration tests** for API endpoints (Django TestCase)
- **End-to-end tests** for user flows (Playwright or Cypress)
- **Mock Spotify API** to avoid rate limits in tests

**2. User Clustering for Collaborative Filtering**
Currently, each user's recommendations are based only on their own data. I'd add:
- **K-means clustering** on user profiles
- Find users with similar listening patterns
- Recommend tracks popular within their cluster
- This is like **true collaborative filtering** (user-user similarity)

**3. Performance Monitoring Dashboard**
Track key metrics:
- Recommendation acceptance rate (% of recommendations users like)
- API response times
- Cost per user per day (OpenAI + infrastructure)
- User engagement metrics (session length, return rate)

**4. Experimentation Framework**
A/B testing different recommendation strategies:
- Test: Increase contextual weight from 20% to 30%
- Measure: Does this improve user engagement?
- Roll out winner to all users

**5. Streaming Integration**
Actually let users play music in-app (Spotify Web Playback SDK) instead of redirecting to Spotify.

**6. Social Features**
- Share playlists generated from recommendations
- See what friends are discovering
- Collaborative recommendation sessions

**7. Production Infrastructure**
- Move to PostgreSQL for production database
- Deploy on AWS/GCP with Docker containers
- Set up CI/CD pipeline (GitHub Actions)
- Implement proper secret management (AWS Secrets Manager)

**But Here's What I'd Prioritize First:**
Given limited time, I'd focus on **testing and monitoring**. You can't improve what you don't measure, and untested code is a liability in production.

**Why This Matters to Your Team:**
You mentioned quarterly goals with 3-4 concrete objectives. This shows I can think strategically about what to build next, balance technical debt with new features, and prioritize based on business value."

**Why This Answer Works**:
- Shows you're always thinking ahead
- Demonstrates understanding of software lifecycle (testing, monitoring, deployment)
- Connects to their process (quarterly goals)
- Realistic about constraints (time, priority)

---

## Questions to Ask THEM

### **About the AI/ML Projects:**

1. **"You mentioned the AI slotting project at the audio manufacturer. How did you approach the problem of deciding which ML models to test - gradient boosting, random forest, and LSTM? What made LSTM relevant for warehouse slotting?"**
   - **Why Ask**: Shows you understand different model types and when to use them
   - **What You're Looking For**: How they frame ML problems and select approaches

2. **"In your AI slotting case study, you found that travel path was the #1 variable affecting pick time. That's a really concrete, actionable insight. How do you balance model complexity with interpretability when delivering results to clients?"**
   - **Why Ask**: Shows you understand production ML is about business value, not just accuracy
   - **What You're Looking For**: Their philosophy on explainable AI

3. **"Your TED system uses real-time location tracking for predictive task assignment. Are you using ML forecasting models for that, or more rule-based logic? And what role do you see AI playing in the future of TED?"**
   - **Why Ask**: Shows interest in their flagship product and where you might contribute
   - **What You're Looking For**: Actual ML opportunities in their products

### **About the Team & Development Process:**

4. **"You mentioned quarterly goals with 3-4 objectives. Can you give me an example of a recent quarter's goals and how you measured success?"**
   - **Why Ask**: Understand how they plan and what "done" looks like
   - **What You're Looking For**: Clarity of goals, how they measure success

5. **"When you identify a weakness during onboarding and assign courses, how do you balance learning time with contributing to sprint work? I want to make sure I'm productive while still growing."**
   - **Why Ask**: Shows you care about contributing value immediately
   - **What You're Looking For**: How supportive they are of learning

6. **"You mentioned small team = impact and visibility. Can you share an example of how a recent junior developer made an impact early on?"**
   - **Why Ask**: Shows you want concrete examples, not just promises
   - **What You're Looking For**: Whether they actually mentor juniors well

### **About the Tech Stack & Collaboration:**

7. **"Your RF Plus integrates with multiple ERP systems. What's the biggest challenge in maintaining those integrations when ERP vendors update their APIs?"**
   - **Why Ask**: Shows you understand integration is ongoing work, not one-and-done
   - **What You're Looking For**: How they handle technical debt and maintenance

8. **"You use GitHub Copilot on the team. How do you balance AI assistance with code review standards? I've found Copilot helpful but it sometimes suggests patterns that don't match project conventions."**
   - **Why Ask**: Shows you've used AI coding tools thoughtfully
   - **What You're Looking For**: Their code quality standards

9. **"In the tech test, you mentioned you're looking for how someone breaks down problems into smaller solutions. Can you give an example of a recent problem one of your developers solved that really impressed you with their approach?"**
   - **Why Ask**: Understand what "good" looks like to them
   - **What You're Looking For**: Their problem-solving philosophy

---

## The 20-Minute Tech Test: What to Expect

**From the Job Info:**
> "20mins for tech test - small problem - be able to see how they solve the problem - not syntax/coding - watch the student interpret the problem, how to break it down to smaller solutions in order to - huge strength is the backend - db, understand the problem, design the database and analyze current database - write sample code at the end, not focussing on syntax - they want to see the idea of the solution"

### **What They're Actually Testing:**

1. **Problem Interpretation** → Can you ask clarifying questions?
2. **Problem Decomposition** → Can you break a big problem into smaller pieces?
3. **Database Design** → Can you model data relationships?
4. **Algorithmic Thinking** → Can you describe a solution approach before coding?
5. **Communication** → Can you explain your thinking clearly?

### **Example Problem (Warehouse Themed):**

**"Design a system to track inventory movement in a warehouse. When items are picked, we need to know who picked them, when, from which location, and for which order. Occasionally, items are returned to different locations. Design the database schema and describe how you'd handle this."**

### **Your Approach (Think Aloud):**

**Step 1: Clarify the Problem (2-3 minutes)**
- "Let me make sure I understand the requirements..."
- "Are we tracking individual items or quantities?"
- "Can one order have multiple items?"
- "Do we need to track the full history or just current location?"
- "Are there different types of locations (receiving, storage, shipping)?"

**Step 2: Identify Entities (2-3 minutes)**
- **Items** (product_id, description, sku)
- **Locations** (location_id, aisle, shelf, zone)
- **Orders** (order_id, customer, created_at)
- **Workers** (worker_id, name, role)
- **Movements** (movement_id, item_id, from_location, to_location, worker_id, timestamp, reason)

**Step 3: Design Relationships (3-4 minutes)**
Draw ERD on whiteboard/paper:
```
Items ←→ Movements ←→ Workers
  ↓
Orders ←→ OrderItems

Locations ←→ Movements (from_location, to_location)
```

**Step 4: Describe Key Queries (3-4 minutes)**
- "To find current location of an item, I'd query the Movements table ordered by timestamp DESC, limit 1"
- "To track worker productivity, I'd aggregate movements grouped by worker_id"
- "For audit trail, I'd keep all movement records (never delete)"

**Step 5: Write Sample Code (3-4 minutes)**
```python
# Not worried about exact syntax, showing the concept

def get_current_location(item_id):
    latest_movement = Movement.objects.filter(
        item_id=item_id
    ).order_by('-timestamp').first()

    if latest_movement:
        return latest_movement.to_location
    return None  # Item not yet in system

def record_pick(item_id, worker_id, from_location, order_id):
    movement = Movement.create(
        item_id=item_id,
        worker_id=worker_id,
        from_location=from_location,
        to_location="SHIPPING",  # Or get from order
        reason="PICK",
        timestamp=now()
    )

    # Update order status
    order_item = OrderItem.objects.get(order_id=order_id, item_id=item_id)
    order_item.picked_at = now()
    order_item.picked_by = worker_id
    order_item.save()

    return movement
```

**Step 6: Discuss Trade-offs (2-3 minutes)**
- "I'm using an event-sourcing approach with the Movements table - this gives us full audit trail but could grow large. We might want to archive old movements after 2 years."
- "Alternative approach: Have a current_location field on Items table for fast lookups, but still keep Movements history"
- "For high-volume warehouses, we'd want to consider partitioning the Movements table by date"

### **What Makes This Answer Strong:**
✅ Asked clarifying questions upfront
✅ Broke problem into clear entities
✅ Explained relationships visually
✅ Described queries in plain English before coding
✅ Showed code as pseudocode (concept > syntax)
✅ Discussed trade-offs and alternatives

---

## Connecting SongScope to Their Business Problems

### **The Parallel: Recommendation Engine ≈ Predictive Warehouse Management**

| **SongScope Challenge** | **Portable Intelligence Challenge** | **Shared Concept** |
|---|---|---|
| Recommend songs user will like | Assign tasks to nearest available worker | **Proximity-based optimization** |
| Learn from like/dislike feedback | Learn from pick time data | **Feedback loop for continuous improvement** |
| Balance discovery vs familiarity | Balance efficiency vs flexibility | **Exploration vs exploitation** |
| Predict user preferences from history | Forecast inventory needs from history | **Pattern recognition in time-series data** |
| Filter out already-known songs | Avoid redundant task assignments | **Deduplication and smart filtering** |
| Adapt to time-of-day listening patterns | Optimize by shift, season, volume | **Contextual adaptation** |
| Respect API rate limits and costs | Respect hardware constraints and costs | **Resource-constrained optimization** |

### **The Pitch:**

"SongScope taught me that the best AI systems aren't just accurate - they're **responsive, adaptive, and resource-aware**.

When I built the hybrid recommendation engine, I wasn't just throwing ML at a problem. I was solving a real-world challenge with real constraints: API limits, cost budgets, user experience expectations.

That's exactly what your AI slotting system does - it doesn't just optimize for theoretical efficiency, it optimizes for **real warehouses with real constraints**: physical layout, seasonal demand, worker availability, hardware costs.

I'm excited about this role because I see the same problems I've been solving in SongScope showing up in your warehouse optimization challenges - just at a much larger scale with much higher stakes. And I'm ready to learn from engineers who've been solving these problems in production for 25 years."

---

## Final Tips for Interview Day

### **Before the Interview:**
1. ✅ Test SongScope live (it's working now!)
2. ✅ Have the original XGBoost notebook open to reference
3. ✅ Review their case studies (AI slotting, TED, RF Plus)
4. ✅ Prepare 2-3 questions for them
5. ✅ Test your camera/mic if remote

### **During the Interview:**
- **Think out loud** - they want to see your process, not just the answer
- **Ask clarifying questions** - shows you don't make assumptions
- **Draw diagrams** - visual communication is powerful
- **Admit what you don't know** - then explain how you'd learn it
- **Connect to their products** - show you researched the company

### **For the Tech Test:**
- **Slow down** - 20 minutes is plenty of time if you structure it
- **Whiteboard first** - draw before coding
- **Explain as you go** - narrate your thought process
- **Focus on backend** - they said DB design is key
- **Ask if you're on the right track** - they'll guide you if you're off

### **Red Flags to Watch For:**
- ❌ Vague answers about junior developer success stories
- ❌ Unrealistic expectations for 20% school time + full sprint work
- ❌ No mention of code review or quality standards
- ❌ Heavy emphasis on "We use AI" without concrete examples

### **Green Flags to Look For:**
- ✅ Specific examples of recent junior developer contributions
- ✅ Clear explanation of quarterly goal setting
- ✅ Enthusiasm about teaching and mentoring
- ✅ Concrete answers about day-to-day work
- ✅ Transparency about challenges and constraints

---

## Key Takeaways

**Your Unique Value Proposition:**

"I bring a rare combination of **academic ML knowledge** (XGBoost, hyperparameter tuning, feature engineering) and **production software experience** (full-stack development, API integration, cost management, error handling).

Most ML students can build a model. Fewer can deploy it to production. Even fewer can build a full application around it that users actually want to use.

SongScope isn't just a portfolio project - it's a real system with real constraints that taught me how ML fits into larger software systems. And that's exactly what Portable Intelligence needs: someone who can bridge the gap between data science theory and production software reality."

---

**You've got this! Your project is impressive and directly relevant. Now go show them what you can do.**