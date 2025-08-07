"use client";

import { useState, useEffect } from "react";
import { AudioPlayer } from "../AudioPlayer/AudioPlayer";
import { AddToLiked } from "../AddToLiked/AddToLiked";
import FeedbackButtonGroup from "../Feedback/FeedbackButtonGroup";
import { get } from "../../../../services/axios";

interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  preview_url: string | null;
  image_url: string | null;
}

interface RecommendationsResponse {
  recommendations: Track[];
}

export default function Recommendation() {
  const [recommendations, setRecommendations] = useState<Track[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch recommendations when the component mounts
  useEffect(() => {
    async function fetchRecommendations() {
      try {
        setLoading(true);
        setError(null);
        
        console.log("Fetching recommendations from API...");
        console.log("Backend URL:", process.env.NEXT_PUBLIC_BACKEND_URL);
        
        // First check if we're authenticated
        try {
          console.log("Current cookies:", document.cookie);
          const authCheck = await get<{authenticated: boolean}>("/api/check-auth/");
          console.log("Auth check:", authCheck);
        } catch (authError) {
          console.error("Auth check failed:", authError);
        }
        
        const response = await get<RecommendationsResponse>("/api/recommendations/");
        
        console.log("API Response:", response);
        
        if (!response.recommendations || !Array.isArray(response.recommendations)) {
          throw new Error("Invalid response format from API");
        }

        // Show all recommendations, even those without preview URLs
        const allRecommendations = response.recommendations;
        
        console.log("All recommendations:", allRecommendations);
        
        if (allRecommendations.length === 0) {
          setError("No recommendations available");
        } else {
          setRecommendations(allRecommendations);
        }
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching recommendations:", err);
        
        let errorMessage = "Failed to fetch recommendations";
        
        if (err instanceof Error) {
          console.error("Error details:", err);
          if (err.message.includes("401")) {
            errorMessage = "Authentication required. Please log in again.";
          } else if (err.message.includes("403")) {
            errorMessage = "Access denied. Please check your Spotify permissions.";
          } else if (err.message.includes("404")) {
            errorMessage = "Recommendations service not found.";
          } else if (err.message.includes("500")) {
            errorMessage = "Server error. Please try again later.";
          } else {
            errorMessage = err.message;
          }
        }
        
        setError(errorMessage);
        setRecommendations([]);
        setLoading(false);
      }
    }

    fetchRecommendations();
  }, []);

  // Handle the next track
  const nextTrack = () => {
    if (currentIndex < recommendations.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  // Handle the previous track
  const previousTrack = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };



  // Handle loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-white text-lg mb-2">Loading recommendations...</div>
          <div className="text-gray-400 text-sm">This may take a moment</div>
        </div>
      </div>
    );
  }

  // Handle error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-2">Error Loading Recommendations</div>
          <div className="text-gray-400 text-sm mb-4">{error}</div>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-green text-black px-4 py-2 rounded hover:bg-green-600 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Handle empty recommendations
  if (recommendations.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-white text-lg mb-2">No Recommendations Available</div>
          <div className="text-gray-400 text-sm">Check back later for new recommendations</div>
        </div>
      </div>
    );
  }

  const currentTrack = recommendations[currentIndex];

  // Safety check for current track
  if (!currentTrack) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-2">Invalid Track Data</div>
          <div className="text-gray-400 text-sm">Please refresh the page</div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex gap-8 lg:gap-12 w-[100%] flex-col md:flex-row p-2 md:p-4 lg:p-8">
      <div className="md:w-[45%] lg:w-[55%] p-2 lg:p-0">
        <img 
          src={currentTrack.image_url || '/images/albums.png'} 
          alt={currentTrack.name}
          onError={(e) => {
            console.error(`Failed to load image for track: ${currentTrack.name}`);
            e.currentTarget.src = '/images/albums.png'; // Fallback image
          }}
          className="w-full h-auto rounded-lg"
        />
      </div>

      <div className="md:w-[55%] lg:w-[45%] flex flex-col gap-8 lg:gap-12 p-2 lg:p-0">
        <div className="flex flex-col gap-4">
          <h3 className="text-2xl lg:text-5xl text-bold text-white">
            {currentTrack.name}
          </h3>
          <h4 className="text-xl text-bold text-white">
            {currentTrack.artist}
          </h4>
          <h4 className="text-xl text-bold text-white">{currentTrack.album}</h4>
        </div>

        <div className="flex flex-col gap-2 p-2">
          <span className="text-white font-light text-sm">Preview</span>
          {currentTrack.preview_url ? (
            <AudioPlayer src={currentTrack.preview_url} />
          ) : (
            <div className="text-gray-400 text-sm">No preview available</div>
          )}
        </div>

        <div className="flex gap-4 lg:gap-8 flex-col lg:flex-row">
          <AddToLiked id={currentTrack.id} />
          <a
            href={`https://open.spotify.com/track/${currentTrack.id}`}
            className="bg-green rounded-full flex items-center justify-center gap-2 flex-1 text-black py-2 text-center hover:scale-105 transition-transform duration-200"
          >
            <img 
              className="w-5 h-5" 
              src="/images/spotify-logo.png" 
              alt="Spotify logo"
              style={{ width: '20px', height: '20px' }}
            />
            <span>Open in Spotify</span>
          </a>
        </div>

        <div className="flex justify-between mt-auto items-center">
          <FeedbackButtonGroup trackId={currentTrack.id} />

          <div className="flex gap-4 items-center">
            {currentIndex > 0 && (
              <button
                onClick={previousTrack}
                className="flex items-center hover:scale-105 transition duration-300 gap-1"
              >
                <img
                  src="/images/arrow_back.png"
                  alt="previous arrow icon"
                  className="w-6 rotate-[90deg]"
                />
                <span className="text-green">Previous</span>
              </button>
            )}

            {currentIndex < recommendations.length - 1 ? (
              <button
                onClick={nextTrack}
                className="flex items-center hover:scale-105 transition duration-300 gap-1"
              >
                <span className="text-green">Next Recommendation</span>
                <img
                  src="/images/arrow_back.png"
                  alt="next arrow icon"
                  className="w-6 rotate-[270deg]"
                />
              </button>
            ) : (
              <div className="text-gray-300">End of Recommendations</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
