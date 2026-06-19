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
            # Build prompt with context
            prompt = self._build_prompt(user_text, track_info)
            
            # Make OpenAI request — response_format guarantees valid JSON output
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
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
    
    def _build_prompt(self, user_text: str, track_info: Dict = None) -> str:
        """Build the prompt for OpenAI"""
        context = ""
        if track_info:
            context = f"\nCurrent track: {track_info.get('name', 'Unknown')} by {track_info.get('artist', 'Unknown')}"
            if track_info.get('genres'):
                context += f"\nTrack genres: {', '.join(track_info['genres'][:4])}"

        return f"""
Analyze this music feedback and extract structured information:
"{user_text}"{context}

Return a JSON object with these fields (use null if not applicable):
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
    "specific_artists": ["artist1", "artist2"] | null,
    "specific_genres": ["genre1", "genre2"] | null,
    "familiarity_context": "already_heard" | "new_discovery" | null,
    "time_context": "morning" | "afternoon" | "evening" | "night" | null,
    "activity_context": "workout" | "relaxation" | "party" | "focus" | "driving" | null,
    "overall_sentiment": "positive" | "negative" | "neutral" | null,
    "confidence": 0.0-1.0
}}

Rules:
- If user says "this genre" or "this type of music" and Track genres are provided, populate specific_genres from the track genres.
- If user says they already know/have heard the track but still like it, set familiarity_context to "already_heard".
- Set overall_sentiment based on the general tone of the feedback: "positive" if the user is satisfied/happy, "negative" if dissatisfied, "neutral" if informational or mixed, null if unclear.
- Only include fields clearly indicated in the feedback. Be conservative - if unsure, use null.
"""
    
    def _fallback_interpretation(self, user_text: str) -> Dict:
        """Fallback interpretation when OpenAI is not available"""
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
            "time_context": None,
            "activity_context": None,
            "overall_sentiment": None,
            "confidence": 0.3
        }
        
        # Simple keyword matching
        if any(word in user_text_lower for word in ["fast", "quick", "upbeat"]):
            interpretation["tempo_preference"] = "faster"
        elif any(word in user_text_lower for word in ["slow", "slower", "downbeat"]):
            interpretation["tempo_preference"] = "slower"
        
        if any(word in user_text_lower for word in ["sad", "depressing", "melancholy"]):
            interpretation["mood_preference"] = "sadder"
        elif any(word in user_text_lower for word in ["happy", "upbeat", "cheerful"]):
            interpretation["mood_preference"] = "happier"
        
        if any(word in user_text_lower for word in ["angry", "aggressive", "intense"]):
            interpretation["energy_preference"] = "higher"
        elif any(word in user_text_lower for word in ["calm", "peaceful", "gentle"]):
            interpretation["energy_preference"] = "lower"

        if any(word in user_text_lower for word in ["love", "great", "amazing", "good", "like"]):
            interpretation["overall_sentiment"] = "positive"
        elif any(word in user_text_lower for word in ["hate", "don't like", "awful", "bad", "dislike", "not"]):
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