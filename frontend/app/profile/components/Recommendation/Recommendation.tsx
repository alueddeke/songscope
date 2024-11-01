import React, { useEffect, useState } from "react";
import { get } from "../../../../services/axios";
import AudioPlayer from "react-h5-audio-player";
import 'react-h5-audio-player/src/styles.scss'
import '../../../../styles/variables.scss';

interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  preview_url: string;
  image_url: string;
}

interface RecommendationsResponse {
  recommendations: Track[];
}

export default function Recommendation() {
  const [recommendations, setRecommendations] = useState<Track[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        const response = await get<RecommendationsResponse>(
          "/api/recommendations/"
        );

        setRecommendations(
          response.recommendations.filter(
            (recommendation) => recommendation.preview_url != undefined
          )
        );
        setLoading(false);
      } catch (err) {
        console.error(err);
        if (err instanceof Error) {
          setError(`Failed to fetch recommendations: ${err.message}`);
        } else {
          setError("An unexpected error occurred");
        }
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, []);

  if (loading) return <div>Loading recommendations...</div>;
  if (error) return <div>{error}</div>;
  console.log(recommendations[0]);

  function addToFavorites() {
    console.log("adding to favs");
  }

  function openinSpotify() {
    console.log("opening in spotify");
  }

  return (
    <div className="mx-auto flex gap-16 w-[100%]">
      <div className="w-[50%]">
        <img src={recommendations[0].image_url} />
      </div>

      <div className="w-[50%] flex flex-col gap-32">
        <div className="flex flex-col gap-4">
          <h3 className="text-5xl text-bold text-white">
            {recommendations[0].name}
          </h3>
          <h4 className="text-xl text-bold text-white">
            {recommendations[0].artist}
          </h4>
          <h4 className="text-xl text-bold text-white">
            {recommendations[0].album}
          </h4>
        </div>

        <div className="flex flex-col gap-2">
            <span className="text-white font-light text-sm">preview</span>
          <AudioPlayer
            src={recommendations[0].preview_url}
            onPlay={(e) => console.log("onPlay")}
            className="rounded-sm"
            style={{backgroundColor: "black", color: "white", accentColor: "white", padding: "1rem 2rem", borderRadius: "4px"}}
            showSkipControls={false}
            showJumpControls={false}
            loop={false}
          />
        </div>

        <div className="flex gap-8">
          <button
            className="bg-green rounded-full flex-1 text-black py-2"
            onClick={addToFavorites}
          >
            Add to Favorites
          </button>
          <button
            className="bg-black rounded-full flex-1 text-white"
            onClick={openinSpotify}
          >
            Open in Spotify
          </button>
        </div>
      </div>
    </div>
  );
}
