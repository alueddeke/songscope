import React, { useEffect, useState } from "react";
import { get } from "../../../../services/axios";

interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  preview_url: string | null;
}

interface RecommendationsResponse {
  recommendations: Track[];
}

export default function Recommendations() {
  const [recommendations, setRecommendations] = useState<Track[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        const response = await get<RecommendationsResponse>(
          "/api/recommendations/"
        );

        console.log(response.recommendations);
        setRecommendations(response.recommendations);
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

  return (
    <div className="container mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Recommended Tracks</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {recommendations.map((track) => (
          <div
            key={track.id}
            className="bg-white shadow-md rounded-lg overflow-hidden hover:shadow-lg transition-shadow duration-300"
          >
            <div className="p-4">
              <h3 className="font-bold text-lg truncate">{track.name}</h3>
              <p className="text-gray-600 truncate">{track.artist}</p>
              <p className="text-gray-500 text-sm truncate">{track.album}</p>
              {track.preview_url ? (
                <div className="mt-3">
                  <audio controls className="w-full h-8">
                    <source src={track.preview_url} type="audio/mpeg" />
                    Your browser does not support the audio element.
                  </audio>
                </div>
              ) : (
                <div className="mt-3">
                  <p className="text-gray-500 text-sm truncate">
                    Song Preview Not Available
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
