"""
AI Feedback Service - OpenAI-powered feedback interpretation

This service interprets natural language feedback from users and converts it
into structured data that can be used by the hybrid recommendation engine.
"""

import json
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from typing import Dict, Optional, List
import time

logger = logging.getLogger(__name__)

class RateLimitMonitor:
    """Monitor OpenAI API rate limits and costs"""
    
    def __init__(self):
        self.openai_requests = []
        self.max_requests_per_minute = 50  # Conservative limit
        self.daily_cost = 0
        self.max_daily_cost = 1.00  # $1/day limit
        self.last_reset = timezone.now().date()
    
    def check_openai_limit(self) -> bool:
        """Check if we can make another OpenAI request"""
        now = timezone.now()
        
        # Reset daily cost if it's a new day
        if now.date() != self.last_reset:
            self.daily_cost = 0
            self.last_reset = now.date()
        
        # Remove requests older than 1 minute
        self.openai_requests = [
            req for req in self.openai_requests 
            if now - req < timedelta(minutes=1)
        ]
        
        if len(self.openai_requests) >= self.max_requests_per_minute:
            logger.warning("OpenAI rate limit exceeded")
            return False
        
        self.openai_requests.append(now)
        return True
    
    def log_cost(self, tokens_used: int):
        """Log the cost of an OpenAI request"""
        cost = (tokens_used / 1000000) * 0.15  # $0.15 per 1M tokens for GPT-4o-mini
        self.daily_cost += cost
        
        if self.daily_cost > self.max_daily_cost:
            logger.error(f"Daily cost limit exceeded: ${self.daily_cost:.4f}")
            raise CostLimitExceeded(f"Daily cost limit exceeded: ${self.daily_cost:.4f}")
        
        logger.info(f"OpenAI request cost: ${cost:.4f}, daily total: ${self.daily_cost:.4f}")

class CostLimitExceeded(Exception):
    """Raised when daily cost limit is exceeded"""
    pass

class FeedbackInterpreter:
    """Interpret natural language feedback using OpenAI"""
    
    def __init__(self):
        self.rate_limiter = RateLimitMonitor()
        self.openai_client = None
        self._initialize_openai()
    
    def _initialize_openai(self):
        """Initialize OpenAI client if API key is available"""
        try:
            from openai import OpenAI
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully")
            else:
                logger.warning("OpenAI API key not found in settings")
        except ImportError:
            logger.error("OpenAI package not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
    
    def interpret_feedback(self, user_text: str, track_info: Dict = None) -> Dict:
        """
        Convert natural language feedback to structured data
        
        Args:
            user_text: User's natural language feedback
            track_info: Optional track information for context
            
        Returns:
            Dict with structured feedback data
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available, using fallback interpretation")
            return self._fallback_interpretation(user_text)
        
        # Check rate limits
        if not self.rate_limiter.check_openai_limit():
            raise RateLimitExceeded("OpenAI rate limit exceeded")
        
        try:
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                *self._get_few_shot_messages(),
                {"role": "user", "content": self._build_prompt(user_text, track_info)},
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=400,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Log cost
            tokens_used = response.usage.total_tokens
            self.rate_limiter.log_cost(tokens_used)
            
            # Parse response
            content = response.choices[0].message.content
            interpretation = json.loads(content)
            
            logger.info(f"AI feedback interpretation: {interpretation}")
            return interpretation
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {str(e)}")
            return self._fallback_interpretation(user_text)
        except Exception as e:
            logger.error(f"OpenAI request failed: {str(e)}")
            return self._fallback_interpretation(user_text)
    
    def _build_system_prompt(self) -> str:
        """System message: schema, vocabulary mapping, and rules for preference extraction."""
        empty_json = json.dumps({
            "tempo_preference": None, "mood_preference": None, "artist_preference": None,
            "genre_preference": None, "energy_preference": None, "valence_preference": None,
            "danceability_preference": None, "acousticness_preference": None,
            "instrumentalness_preference": None, "specific_artists": None,
            "specific_genres": None, "familiarity_context": None, "time_context": None,
            "activity_context": None, "overall_sentiment": None, "confidence": 0.5,
        })
        return f"""You are a music preference extractor. Given a user's natural-language feedback about a song recommendation, return a single JSON object with the fields below. Use null for fields not mentioned or not clearly implied.

OUTPUT SCHEMA — return all 16 fields every time:
{{
  "tempo_preference": "slower" | "faster" | null,
  "mood_preference": "happier" | "sadder" | "calmer" | "more energetic" | "less energetic" | null,
  "artist_preference": "avoid_artist" | "prefer_artist" | null,
  "genre_preference": "avoid_genre" | "prefer_genre" | null,
  "energy_preference": "lower" | "higher" | null,
  "valence_preference": "happier" | "sadder" | null,
  "danceability_preference": "more_danceable" | "less_danceable" | null,
  "acousticness_preference": "more_acoustic" | "less_acoustic" | null,
  "instrumentalness_preference": "more_instrumental" | "less_instrumental" | null,
  "specific_artists": ["name"] | null,
  "specific_genres": ["genre"] | null,
  "familiarity_context": "already_heard" | "new_discovery" | null,
  "time_context": "morning" | "afternoon" | "evening" | "night" | null,
  "activity_context": "workout" | "relaxation" | "party" | "focus" | "driving" | null,
  "overall_sentiment": "positive" | "negative" | "neutral" | null,
  "confidence": 0.0-1.0
}}

VOCABULARY MAPPING — use these exact mappings:

Vocals / singing:
  "vocals", "with vocals", "has singing", "someone singing", "sung", "lyrics", "singer"
    → instrumentalness_preference: "less_instrumental"
  "no vocals", "without vocals", "purely instrumental", "no singing", "instrumental only"
    → instrumentalness_preference: "more_instrumental"

Energy / intensity:
  "energetic", "more energy", "high energy", "upbeat", "hype", "banger", "bangers",
  "hard-hitting", "pump up", "intense", "powerful"
    → energy_preference: "higher", mood_preference: "more energetic"
  "chill", "mellow", "relaxed", "laid-back", "calm", "less intense", "soft", "gentle",
  "wind down", "easy listening"
    → energy_preference: "lower", mood_preference: "calmer"

Tempo:
  "faster", "quicker", "speed it up", "fast tempo"  → tempo_preference: "faster"
  "slower", "slow it down", "slow tempo"            → tempo_preference: "slower"

Mood / valence:
  "happy", "uplifting", "feel-good", "positive vibes", "cheerful", "fun"
    → valence_preference: "happier"
  "sad", "melancholy", "dark", "gloomy", "depressing"
    → valence_preference: "sadder"

Genre avoidance — "no X" / "without X" / "avoid X" / "not X" for any genre name:
  Set genre_preference: "avoid_genre" and specific_genres: [X]
  Examples: "no ambient" → specific_genres: ["ambient"]
            "avoid jazz"  → specific_genres: ["jazz"]
            "not classical" → specific_genres: ["classical"]

Genre preference — "more X" / "give me X" for any genre name:
  Set genre_preference: "prefer_genre" and specific_genres: [X]

Familiarity / discovery:
  "haven't heard", "never heard", "not heard before", "something new", "new to me",
  "discover", "unfamiliar", "don't know it", "haven't listened to", "fresh",
  "something I don't know", "new music", "undiscovered"
    → familiarity_context: "new_discovery"
  "already heard", "know this", "heard this before", "I've heard this",
  "already know", "heard it already"
    → familiarity_context: "already_heard"

RULES:
1. NEGATION: "no X", "without X", "avoid X", "not X", "don't want X" → extract X as avoidance.
   For a genre: genre_preference: "avoid_genre", specific_genres: [X].
   For a feature: set the OPPOSITE direction (e.g. "no energy" → energy_preference: "lower").
2. MULTI-SIGNAL: Extract ALL preferences mentioned. "more energetic with vocals" → set BOTH
   energy_preference AND instrumentalness_preference.
3. INFER: If context strongly implies a preference, extract it. "morning run" → activity_context:
   "workout", energy_preference: "higher". Do NOT default to null when context is clear.
4. GENRE CONTEXT: If user says "this genre" / "this type of music" and track genres are listed,
   populate specific_genres from those genres.
5. FAMILIARITY: "already know this", "I've heard this before" → familiarity_context: "already_heard".
   "haven't heard this", "something new", "discover" → familiarity_context: "new_discovery".
   Both can co-exist with genre/artist preferences (e.g. "indie rock I haven't heard" → BOTH
   genre_preference: "prefer_genre", specific_genres: ["indie rock"], AND familiarity_context: "new_discovery").
6. SENTIMENT: positive if satisfied, negative if dissatisfied, neutral if informational/mixed.
7. CONFIDENCE: 0.8-1.0 for explicit preferences, 0.5-0.7 for inferred, 0.3-0.4 if uncertain.

Empty-feedback baseline (use as template): {empty_json}"""

    def _get_few_shot_messages(self) -> list:
        """Three few-shot user/assistant pairs covering the most commonly misinterpreted patterns."""
        ex1_out = json.dumps({
            "tempo_preference": None, "mood_preference": None, "artist_preference": None,
            "genre_preference": None, "energy_preference": None, "valence_preference": None,
            "danceability_preference": None, "acousticness_preference": None,
            "instrumentalness_preference": "more_instrumental", "specific_artists": None,
            "specific_genres": None, "familiarity_context": None, "time_context": None,
            "activity_context": None, "overall_sentiment": "negative", "confidence": 0.95,
        })
        ex2_out = json.dumps({
            "tempo_preference": "faster", "mood_preference": "more energetic",
            "artist_preference": None, "genre_preference": None, "energy_preference": "higher",
            "valence_preference": None, "danceability_preference": "more_danceable",
            "acousticness_preference": None, "instrumentalness_preference": None,
            "specific_artists": None, "specific_genres": None, "familiarity_context": None,
            "time_context": None, "activity_context": "workout", "overall_sentiment": "neutral",
            "confidence": 0.9,
        })
        ex3_out = json.dumps({
            "tempo_preference": None, "mood_preference": "more energetic",
            "artist_preference": None, "genre_preference": "avoid_genre",
            "energy_preference": "higher", "valence_preference": None,
            "danceability_preference": "more_danceable", "acousticness_preference": None,
            "instrumentalness_preference": "less_instrumental",
            "specific_artists": None, "specific_genres": ["ambient"],
            "familiarity_context": None, "time_context": None, "activity_context": None,
            "overall_sentiment": "negative", "confidence": 0.95,
        })
        ex4_out = json.dumps({
            "tempo_preference": None, "mood_preference": None, "artist_preference": None,
            "genre_preference": "prefer_genre", "energy_preference": None, "valence_preference": None,
            "danceability_preference": None, "acousticness_preference": None,
            "instrumentalness_preference": None, "specific_artists": None,
            "specific_genres": ["indie rock"], "familiarity_context": "new_discovery",
            "time_context": None, "activity_context": None, "overall_sentiment": "neutral",
            "confidence": 0.95,
        })
        return [
            {"role": "user", "content": 'Feedback: "I hate hearing vocals, give me something purely instrumental"'},
            {"role": "assistant", "content": ex1_out},
            {"role": "user", "content": 'Feedback: "More energetic please, I\'m working out"'},
            {"role": "assistant", "content": ex2_out},
            {"role": "user", "content": 'Feedback: "No more ambient music, give me something with a beat and vocals"'},
            {"role": "assistant", "content": ex3_out},
            {"role": "user", "content": 'Feedback: "Give me some indie rock I haven\'t heard before"'},
            {"role": "assistant", "content": ex4_out},
        ]

    def _build_prompt(self, user_text: str, track_info: Dict = None) -> str:
        """Build the user turn: feedback text + optional track context."""
        context = ""
        if track_info:
            context = f"\nCurrent track: {track_info.get('name', 'Unknown')} by {track_info.get('artist', 'Unknown')}"
            if track_info.get('genres'):
                context += f"\nTrack genres: {', '.join(track_info['genres'][:4])}"
        return f'Feedback: "{user_text}"{context}'
    
    def _fallback_interpretation(self, user_text: str) -> Dict:
        """Fallback interpretation when OpenAI is not available"""
        import re
        user_text_lower = user_text.lower()

        interpretation = {
            "tempo_preference": None,
            "mood_preference": None,
            "artist_preference": None,
            "genre_preference": None,
            "energy_preference": None,
            "valence_preference": None,
            "danceability_preference": None,
            "acousticness_preference": None,
            "instrumentalness_preference": None,
            "specific_artists": None,
            "specific_genres": None,
            "familiarity_context": None,
            "time_context": None,
            "activity_context": None,
            "overall_sentiment": None,
            "confidence": 0.3,
        }

        # Tempo
        if any(w in user_text_lower for w in ["fast", "quick", "faster", "speed up"]):
            interpretation["tempo_preference"] = "faster"
        elif any(w in user_text_lower for w in ["slow", "slower", "slow down"]):
            interpretation["tempo_preference"] = "slower"

        # Mood / valence
        if any(w in user_text_lower for w in ["sad", "depressing", "melancholy", "gloomy", "dark"]):
            interpretation["mood_preference"] = "sadder"
            interpretation["valence_preference"] = "sadder"
        elif any(w in user_text_lower for w in ["happy", "cheerful", "uplifting", "feel good", "fun"]):
            interpretation["mood_preference"] = "happier"
            interpretation["valence_preference"] = "happier"

        # Energy — covers the "energetic/banger" pattern the AI was missing
        if any(w in user_text_lower for w in [
            "energetic", "more energy", "high energy", "banger", "bangers",
            "hype", "pump up", "intense", "powerful", "angry", "aggressive",
        ]):
            interpretation["energy_preference"] = "higher"
            interpretation["mood_preference"] = "more energetic"
        elif any(w in user_text_lower for w in [
            "calm", "chill", "mellow", "relaxed", "laid-back", "peaceful",
            "gentle", "soft", "wind down", "easy listening",
        ]):
            interpretation["energy_preference"] = "lower"
            interpretation["mood_preference"] = "calmer"

        # Instrumentalness / vocals — check negations BEFORE bare keyword matches
        if any(w in user_text_lower for w in [
            "no vocals", "without vocals", "purely instrumental", "instrumental only",
            "no singing",
        ]):
            interpretation["instrumentalness_preference"] = "more_instrumental"
        elif any(w in user_text_lower for w in [
            "vocal", "vocals", "singing", "sung", "lyrics", "singer", "with vocals",
        ]):
            interpretation["instrumentalness_preference"] = "less_instrumental"

        # Genre avoidance — "no ambient", "avoid jazz", "not classical" etc.
        _KNOWN_GENRES = {
            "ambient", "classical", "jazz", "metal", "rock", "pop", "country",
            "electronic", "folk", "reggae", "blues", "rap", "hip-hop", "indie",
            "punk", "soul", "rnb", "r&b", "dance", "edm", "house", "techno",
            "acoustic", "new age",
        }
        avoid_match = re.search(
            r'\b(?:no|not|without|avoid|stop)\s+([a-z][a-z&-]*)\b',
            user_text_lower,
        )
        if avoid_match:
            candidate = avoid_match.group(1).strip()
            if candidate in _KNOWN_GENRES:
                interpretation["genre_preference"] = "avoid_genre"
                interpretation["specific_genres"] = [candidate]

        # Familiarity / discovery
        if any(w in user_text_lower for w in [
            "haven't heard", "never heard", "not heard", "something new", "new to me",
            "haven't listened", "don't know it", "undiscovered", "fresh music",
            "new music", "discover", "unfamiliar",
        ]):
            interpretation["familiarity_context"] = "new_discovery"
        elif any(w in user_text_lower for w in [
            "already heard", "heard before", "heard this", "know this", "already know",
            "i've heard",
        ]):
            interpretation["familiarity_context"] = "already_heard"

        # Sentiment
        if any(w in user_text_lower for w in ["love", "great", "amazing", "good", "like"]):
            interpretation["overall_sentiment"] = "positive"
        elif any(w in user_text_lower for w in [
            "hate", "don't like", "awful", "bad", "dislike", "no more",
            "stop", "not", "terrible",
        ]):
            interpretation["overall_sentiment"] = "negative"

        return interpretation

class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass


# Module-level singleton — daily_cost and request history persist across requests
# within a single worker process. Better than resetting to 0 per request.
_interpreter_instance: 'FeedbackInterpreter | None' = None


def get_feedback_interpreter() -> 'FeedbackInterpreter':
    global _interpreter_instance
    if _interpreter_instance is None:
        _interpreter_instance = FeedbackInterpreter()
    return _interpreter_instance