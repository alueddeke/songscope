import axios from "axios";
import React, { useEffect, useState } from "react";

interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  image_url: string;
}

export default function TopTracks() {
  const [topTracks, setTopTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTopTracks = async () => {
      try {
        const response = await axios.get<{ tracks: Track[] }>(
          "http://localhost:8000/api/user-top-tracks/",
          { withCredentials: true }
        );
        setTopTracks(response.data.tracks);
        setLoading(false);
      } catch (err) {
        console.error(err);
        if (axios.isAxiosError(err)) {
          if (err.response?.status === 401) {
            setError("Please log in to view your top tracks");
          } else {
            setError(`Failed to fetch top tracks: ${err.response?.statusText}`);
          }
        } else {
          setError("An unexpected error occurred");
        }
        setLoading(false);
      }
    };

    fetchTopTracks();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div className="container mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Your Top Tracks</h2>
      <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {topTracks.map((track) => (
          <li
            key={track.id}
            className="bg-white shadow-md rounded-lg overflow-hidden"
          >
            <img
              src={track.image_url}
              alt={track.name}
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="font-bold text-lg">{track.name}</h3>
              <p className="text-gray-600">{track.artist}</p>
              <p className="text-gray-500 text-sm">{track.album}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
