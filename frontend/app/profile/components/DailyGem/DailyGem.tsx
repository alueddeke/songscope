"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { get } from "../../../../services/axios";
import FeedbackButtonGroup from "../Feedback/FeedbackButtonGroup";
import ScoreBreakdown from "./ScoreBreakdown";
import AIFeedbackInput from "../Feedback/AIFeedbackInput";
import { AddToLiked } from "../AddToLiked/AddToLiked";
import { AudioPlayer } from "../AudioPlayer/AudioPlayer";

interface GemTrack {
  id: string;
  name: string;
  artist: string;
  album: string;
  popularity: number;
  image_url: string | null;
  preview_url: string | null;
}

interface DailyGemResponse {
  track: GemTrack;
  explanation: string;
  score_breakdown: Record<string, number>;
  date: string;
  cached: boolean;
  was_saved?: boolean;
}

function popularityLabel(score: number): { label: string; color: string } {
  if (score < 20) return { label: "Ultra rare", color: "text-purple-400" };
  if (score < 40) return { label: "Hidden gem", color: "text-green" };
  return { label: "Under the radar", color: "text-blue-400" };
}

export default function DailyGem() {
  const [gem, setGem] = useState<DailyGemResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewGemPrompt, setShowNewGemPrompt] = useState(false);
  const [likePrompt, setLikePrompt] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [aiSyncedFeedback, setAiSyncedFeedback] = useState<'LIKE' | 'DISLIKE' | null>(null);

  const fetchGem = async (forceNew = false) => {
    try {
      setLoading(true);
      setError(null);
      setShowNewGemPrompt(false);
      setLikePrompt(false);
      setAiSyncedFeedback(null);
      const url = forceNew ? "/api/daily-gem/?force_new=true" : "/api/daily-gem/";
      const data = await get<DailyGemResponse>(url);
      setGem(data);
      window.dispatchEvent(new CustomEvent('songscope:new-gem'));
    } catch (err) {
      setError("Could not load today's gem. Try refreshing.");
      console.error("DailyGem fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGem();
  }, []);

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

  if (error || !gem) {
    return (
      <div className="w-full flex items-center justify-center min-h-[40vh]">
        <div className="text-center">
          <p className="text-red-400 mb-3">{error ?? "No gem available"}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-green text-black px-5 py-2 rounded-full text-sm font-semibold hover:scale-105 transition-transform"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  const { track, explanation, date, score_breakdown, was_saved } = gem;
  const pop = popularityLabel(track.popularity);
  const formattedDate = new Date(date + "T00:00:00").toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="w-full flex flex-col md:flex-row gap-8 lg:gap-16 items-center">
      {/* Album art */}
      <div className="w-full md:w-[45%] flex-shrink-0">
        <div className="relative aspect-square w-full max-w-[480px] mx-auto rounded-xl overflow-hidden shadow-2xl">
          <Image
            src={track.image_url ?? "/images/albums.png"}
            alt={`${track.name} by ${track.artist}`}
            fill
            sizes="(max-width: 768px) 90vw, 45vw"
            style={{ objectFit: "cover" }}
            priority
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src = "/images/albums.png";
            }}
          />
        </div>
      </div>

      {/* Track details */}
      <div className="w-full md:w-[55%] flex flex-col gap-6">
        {/* Header badge */}
        <div className="flex items-center gap-3">
          <span className="text-green text-xs font-bold uppercase tracking-widest">
            Today's Gem
          </span>
          <span className="text-gray-600 text-xs">·</span>
          <span className="text-gray-500 text-xs">{formattedDate}</span>
        </div>

        {/* Track name + artist */}
        <div>
          <h2 className="text-3xl lg:text-5xl font-bold text-white leading-tight">
            {track.name}
          </h2>
          <p className="text-xl text-gray-300 mt-2">{track.artist}</p>
          <p className="text-gray-500 text-sm mt-1">{track.album}</p>
        </div>

        {/* Popularity badge */}
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${pop.color}`}>
            ♦ {pop.label}
          </span>
          <span className="text-gray-600 text-xs">·</span>
          <span className="text-gray-400 text-xs">
            {track.popularity}/100 popularity — most listeners have never heard this
          </span>
        </div>

        {/* AI explanation — only render when non-empty to avoid orphan border */}
        {explanation && (
          <blockquote className="border-l-2 border-green pl-4 py-1">
            <p className="text-gray-300 italic text-sm leading-relaxed">{explanation}</p>
          </blockquote>
        )}

        {/* Score breakdown */}
        <ScoreBreakdown breakdown={score_breakdown ?? {}} />

        {/* Audio preview */}
        {track.preview_url && (
          <div className="flex flex-col gap-1">
            <span className="text-gray-500 text-xs uppercase tracking-wider">Preview</span>
            <AudioPlayer src={track.preview_url} />
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-4 items-center">
          <AddToLiked id={track.id} initialLiked={was_saved ?? false} />
          <a
            href={`https://open.spotify.com/track/${track.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-green text-black font-semibold rounded-full flex items-center gap-2 px-5 py-2 hover:scale-105 transition-transform text-sm"
          >
            <img src="/images/spotify-logo.png" alt="Spotify" className="w-4 h-4" />
            Open in Spotify
          </a>
        </div>

        <FeedbackButtonGroup
          trackId={track.id}
          onDislike={() => { setShowNewGemPrompt(true); setLikePrompt(false); }}
          onLike={() => { setLikePrompt(true); setShowNewGemPrompt(false); }}
          syncedFeedback={aiSyncedFeedback}
        />

        {/* Natural language feedback */}
        <div className="pt-4 border-t border-gray-800">
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-3">Tell us more</p>
          <AIFeedbackInput
            trackId={track.id}
            onFeedbackSubmitted={(interpretation) => {
              setShowFeedbackModal(true);
              if (interpretation?.overall_sentiment === 'positive') setAiSyncedFeedback('LIKE');
              else if (interpretation?.overall_sentiment === 'negative') setAiSyncedFeedback('DISLIKE');
            }}
          />
        </div>

        {/* Prompts after feedback */}
        {likePrompt && (
          <div className="pt-4 border-t border-gray-800 flex flex-col gap-2">
            <p className="text-gray-400 text-sm">Glad you liked it. Want something similar?</p>
            <button
              onClick={() => { setLikePrompt(false); fetchGem(true); }}
              className="bg-green text-black font-semibold rounded-full px-5 py-2 hover:scale-105 transition-transform text-sm w-fit"
            >
              Find me another
            </button>
          </div>
        )}
        {showNewGemPrompt && (
          <div className="pt-4 border-t border-gray-800 flex flex-col gap-2">
            <p className="text-gray-400 text-sm">Not feeling this one?</p>
            <button
              onClick={() => fetchGem(true)}
              className="bg-green text-black font-semibold rounded-full px-5 py-2 hover:scale-105 transition-transform text-sm w-fit"
            >
              Find me another song
            </button>
          </div>
        )}

        {/* Dev shortcut — always visible, low-key */}
        <div className="pt-2">
          <button
            onClick={() => fetchGem(true)}
            className="text-gray-600 text-xs hover:text-gray-400 transition-colors"
          >
            Generate new gem
          </button>
        </div>
      </div>

      {/* Modal: prompt after AI feedback submitted */}
      {showFeedbackModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-[90vw] max-w-sm shadow-2xl flex flex-col gap-4">
            <p className="text-white font-semibold text-base">Find a new song based on your feedback?</p>
            <p className="text-gray-400 text-sm">Your preferences have been saved. Generate a new gem now or keep listening.</p>
            <div className="flex gap-3 mt-1">
              <button
                onClick={() => {
                  setShowFeedbackModal(false);
                  fetchGem(true);
                }}
                className="flex-1 bg-green text-black font-semibold rounded-full py-2 text-sm hover:scale-105 transition-transform"
              >
                Yes, find me one
              </button>
              <button
                onClick={() => setShowFeedbackModal(false)}
                className="flex-1 bg-gray-800 text-gray-300 font-semibold rounded-full py-2 text-sm hover:bg-gray-700 transition-colors"
              >
                Not yet
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
