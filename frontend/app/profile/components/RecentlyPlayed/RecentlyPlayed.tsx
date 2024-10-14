import React, { useEffect, useState } from "react";
import { get } from "../../../../services/axios";

interface RecentTrack {
  id: string;
  name: string;
  artist: string;
  played_at: string;
}

export default function RecentlyPlayed() {
  const [recentTracks, setRecentTracks] = useState<RecentTrack[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecentTracks = async () => {
      try {
        // First, check if the user is authenticated
        const authResponse = await get<{ authenticated: boolean }>(
          "/api/check-auth/"
        );
        if (!authResponse.authenticated) {
          throw new Error("User is not authenticated");
        }

        const response = await get<{ recent_tracks: RecentTrack[] }>(
          "/api/user-recently-played/"
        );
        setRecentTracks(response.recent_tracks);
        setLoading(false);
      } catch (err) {
        console.error(err);
        if (err instanceof Error) {
          setError(`Failed to fetch recent tracks: ${err.message}`);
        } else {
          setError("An unexpected error occurred");
        }
        setLoading(false);
      }
    };

    fetchRecentTracks();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div className="container mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Recently Played Tracks</h2>
      <ul className="space-y-2">
        {recentTracks.map((track) => (
          <li
            key={`${track.id}-${track.played_at}`}
            className="bg-white shadow p-2 rounded"
          >
            <p className="font-semibold">{track.name}</p>
            <p className="text-sm text-gray-600">{track.artist}</p>
            <p className="text-xs text-gray-500">
              {new Date(track.played_at).toLocaleString()}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
