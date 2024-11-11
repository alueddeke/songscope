"use client";

import { useState, useEffect } from "react";
import { AudioPlayer } from "../AudioPlayer/AudioPlayer";
import { AddToLiked } from "../AddToLiked/AddToLiked";
import FeedbackButtonGroup from "../Feedback/FeedbackButtonGroup";
import arrow from "../../../../public/images/arrow_back.png";

interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  preview_url: string;
  image_url: string;
}

export default function Recommendation() {
  const [recommendations, setRecommendations] = useState<Track[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);

  // Fetch recommendations when the component mounts
  useEffect(() => {
    async function fetchRecommendations() {
      const response = await fetch(
        "http://localhost:8000/api/recommendations/",
        {
          method: "GET",
          credentials: "include", // This ensures the cookies are sent with the request
        }
      );

      if (!response.ok) {
        throw new Error("Failed to fetch recommendations");
      }

      const data = await response.json();
      const filteredRecommendations = data.recommendations.filter(
        (track: Track) => track.preview_url !== null
      );
      setRecommendations(filteredRecommendations);
    }

    fetchRecommendations().catch((err) => {
      console.error(err);
    });
  }, []);

  // Handle the next track
  const nextTrack = () => {
    if (currentIndex < recommendations.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  if (recommendations.length === 0) {
    return <div>Loading...</div>;
  }

  const currentTrack = recommendations[currentIndex];

  return (
    <div className="mx-auto flex gap-8 lg:gap-16 w-[100%] flex-col md:flex-row p-2 md:p-4 lg:p-8">
      <div className="md:w-[45%] lg:w-[55%] p-2 lg:p-0">
        <img src={currentTrack.image_url} alt={currentTrack.name} />
      </div>

      <div className="md:w-[55%] lg:w-[45%] flex flex-col gap-8 lg:gap-16 p-2 lg:p-0">
        <div className="flex flex-col gap-4">
          <h3 className="text-2xl lg:text-5xl text-bold text-white">
            {currentTrack.name}
          </h3>
          <h4 className="text-xl text-bold text-white">
            {currentTrack.artist}
          </h4>
          <h4 className="text-xl text-bold text-white">{currentTrack.album}</h4>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-white font-light text-sm">Preview</span>
          <AudioPlayer src={currentTrack.preview_url} />
        </div>

        <div className="flex gap-4 lg:gap-8 flex-col lg:flex-row">
          <AddToLiked id={currentTrack.id} />
          <a
            href={`https://open.spotify.com/track/${currentTrack.id}`}
            className="bg-black rounded-full flex-1 text-white py-2 text-center hover:scale-105 transition-transform duration-200"
          >
            Open in Spotify
          </a>
        </div>

        <div className="flex justify-between  mt-auto">

          <FeedbackButtonGroup trackId={currentTrack.id} />

          <div className="flex gap-4">
            <button onClick={nextTrack} className="flex items-center hover:scale-105 transition duration-300 gap-1">
              <span className="text-green">Next Suggestion</span>
              <img
                src="/images/arrow_back.png"
                alt="down arrow icon"
                className="w-6 rotate-[270deg]"
              />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
