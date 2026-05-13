'use client'

import { useState, useEffect } from "react";
import { post } from "@/services/axios";
import { Send, Loader2, Sparkles, HelpCircle } from "lucide-react";

interface AIFeedbackInputProps {
  trackId?: string;
  onFeedbackSubmitted?: (interpretation: any) => void;
}

interface AIFeedbackResponse {
  status: string;
  interpretation?: any;
  confidence?: number;
  error?: string;
}

// Rotating placeholder suggestions
const PLACEHOLDER_SUGGESTIONS = [
  "Tell us what you think... (e.g., 'too fast', 'too sad', 'don't want this artist today')",
  "'This song is too fast and angry'",
  "'I want something calmer and more acoustic'",
  "'Don't recommend this artist today'",
  "'I need happier music for my workout'",
  "'This is too slow and depressing'",
  "'I want something more energetic'",
  "'Too electronic for right now'",
  "'I need focus music for studying'",
  "'This genre isn't working for me today'"
];

// Tips for best results
const TIPS_FOR_BEST_RESULTS = [
  "🎯 Be Specific: 'Too fast' works better than 'I don't like this'",
  "😊 Use Emotion Words: 'sad', 'angry', 'happy', 'calm'",
  "⏰ Mention Context: 'for my workout', 'for studying', 'for relaxation'",
  "🎤 Name Artists/Genres: 'Don't recommend Drake', 'Avoid hip-hop'",
  "🔄 Combine Multiple: 'Too fast and angry for right now'",
  "💡 Examples: 'too energetic', 'too mellow', 'not in the mood for this artist'"
];

export default function AIFeedbackInput({ trackId, onFeedbackSubmitted }: AIFeedbackInputProps) {
  const [feedbackText, setFeedbackText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [interpretation, setInterpretation] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentPlaceholderIndex, setCurrentPlaceholderIndex] = useState(0);
  const [showTooltip, setShowTooltip] = useState(false);
  const [isPlaceholderTransitioning, setIsPlaceholderTransitioning] = useState(false);

  // Rotate placeholders every 3 seconds with smooth transition
  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;
    const interval = setInterval(() => {
      setIsPlaceholderTransitioning(true);
      timeoutId = setTimeout(() => {
        setCurrentPlaceholderIndex((prev) =>
          (prev + 1) % PLACEHOLDER_SUGGESTIONS.length
        );
        setIsPlaceholderTransitioning(false);
      }, 250);
    }, 3000);

    return () => {
      clearInterval(interval);
      clearTimeout(timeoutId);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!feedbackText.trim()) return;
    
    setIsSubmitting(true);
    setError(null);
    setInterpretation(null);

    try {
      const response = await post<AIFeedbackResponse>("/api/submit-ai-feedback/", {
        feedback_text: feedbackText.trim(),
        track_id: trackId || "",
      });

      if (response.status === 'success' && response.interpretation) {
        setInterpretation(response.interpretation);
        onFeedbackSubmitted?.(response.interpretation);
        
        // Clear input after successful submission
        setFeedbackText("");
        
        // Clear interpretation after 5 seconds
        setTimeout(() => {
          setInterpretation(null);
        }, 5000);
      } else {
        setError(response.error || "Failed to process feedback");
      }
    } catch (err: any) {
      console.error("Error submitting AI feedback:", err);
      
      if (err.response?.status === 429) {
        if (err.response?.data?.status === 'rate_limit_exceeded') {
          setError("Rate limit exceeded. Please try again later.");
        } else if (err.response?.data?.status === 'cost_limit_exceeded') {
          setError("Daily cost limit exceeded. Please try again tomorrow.");
        } else {
          setError("Too many requests. Please try again later.");
        }
      } else {
        setError("Failed to process feedback. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const getInterpretationSummary = (interpretation: any) => {
    const changes = [];
    
    if (interpretation.tempo_preference) {
      changes.push(`Tempo: ${interpretation.tempo_preference}`);
    }
    if (interpretation.mood_preference) {
      changes.push(`Mood: ${interpretation.mood_preference}`);
    }
    if (interpretation.energy_preference) {
      changes.push(`Energy: ${interpretation.energy_preference}`);
    }
    if (interpretation.specific_artists?.length) {
      changes.push(`Artists: ${interpretation.specific_artists.join(", ")}`);
    }
    if (interpretation.specific_genres?.length) {
      changes.push(`Genres: ${interpretation.specific_genres.join(", ")}`);
    }
    
    return changes.length > 0 ? changes.join(", ") : "No specific changes detected";
  };

  return (
    <div className="w-full">
      {/* AI Feedback Input */}
      <form onSubmit={handleSubmit} className="mb-4">
        <div className="flex gap-2 items-center">
          <div className="flex-1 relative">
            <input
              type="text"
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder={PLACEHOLDER_SUGGESTIONS[currentPlaceholderIndex]}
              className={`w-full px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-green focus:outline-none transition-all duration-300 ${
                isPlaceholderTransitioning ? 'placeholder-transition' : ''
              }`}
              disabled={isSubmitting}
            />
            <Sparkles className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-green" />
          </div>
          
          {/* Help Tooltip Button */}
          <div className="relative">
            <button
              type="button"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              className="p-2 text-gray-400 hover:text-green transition-colors"
              title="Tips for best results"
            >
              <HelpCircle className="w-5 h-5" />
            </button>
            
            {/* Tooltip */}
            {showTooltip && (
              <div className="absolute bottom-full right-0 mb-2 w-80 bg-gray-900 border border-gray-600 rounded-lg p-4 shadow-xl z-50 tooltip-fade-in">
                <div className="text-green font-medium mb-2">💡 Tips for Best Results:</div>
                <ul className="text-sm text-gray-300 space-y-1">
                  {TIPS_FOR_BEST_RESULTS.map((tip, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-green text-xs mt-1">•</span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
                <div className="text-xs text-gray-400 mt-3">
                  Hover over examples to see more suggestions!
                </div>
              </div>
            )}
          </div>
          
          <button
            type="submit"
            disabled={isSubmitting || !feedbackText.trim()}
            className="px-4 py-2 bg-green text-black rounded-lg hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            {isSubmitting ? "Processing..." : "Send"}
          </button>
        </div>
      </form>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Interpretation Result */}
      {interpretation && (
        <div className="mb-4 p-4 bg-green/10 border border-green/30 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-green" />
            <span className="text-green font-medium">AI Interpretation</span>
            {interpretation.confidence && (
              <span className="text-xs text-gray-400">
                Confidence: {(interpretation.confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>
          <p className="text-white text-sm">
            {getInterpretationSummary(interpretation)}
          </p>
          <p className="text-gray-400 text-xs mt-2">
            Your feedback has been processed and will influence future recommendations.
          </p>
        </div>
      )}

      {/* Quick Examples */}
      <div className="text-gray-400 text-xs">
        <p className="mb-2 font-medium">Quick Examples:</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <div className="space-y-1">
            <div className="text-green">Tempo & Energy:</div>
            <ul className="space-y-1 text-xs">
              <li>• "too fast"</li>
              <li>• "too slow"</li>
              <li>• "too energetic"</li>
              <li>• "too mellow"</li>
            </ul>
          </div>
          <div className="space-y-1">
            <div className="text-green">Mood & Style:</div>
            <ul className="space-y-1 text-xs">
              <li>• "too sad"</li>
              <li>• "too happy"</li>
              <li>• "too angry"</li>
              <li>• "too calm"</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
} 