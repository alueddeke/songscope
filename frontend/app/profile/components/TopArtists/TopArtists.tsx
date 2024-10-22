import React, { useEffect, useState } from "react";
import { get } from "../../../../services/axios";

interface Artist {
  id: string;
  name: string;
  genres: string[];
  popularity: number;
}

export default function TopArtists() {
  const [topArtists, setTopArtists] = useState<Artist[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTopArtists = async () => {
      try {
        const authResponse = await get<{ authenticated: Boolean }>(
          "api/check-auth/"
        );
        if (!authResponse.authenticated) {
          throw new Error("User not authenticated");
        }

        const response = await get<{ top_artists: Artist[] }>(
          "api/user-top-artists/"
        );
        setTopArtists(response.top_artists);
        setLoading(false);
      } catch (err) {
        console.error(err);
        if (err instanceof Error) {
          setError(`Failed to fetch top artists: ${err.message}`);
        } else {
          setError("An unexpected Error occured");
        }
      }
    };

    fetchTopArtists();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div className="container mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Your Top Artists</h2>
      <ul className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {topArtists.map((artist) => (
          <li key={artist.id} className="bg-white shadow-md rounded-lg p-4">
            <h3 className="font-bold text-lg">{artist.name}</h3>
            <p className="text-sm text-gray-600">
              Popularity: {artist.popularity}
            </p>
            <p className="text-xs text-gray-500">{artist.genres.join(", ")}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
