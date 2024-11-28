"use client";

import React, { useEffect, useState } from "react";
import { get } from "../../../../services/axios";

interface Artist {
  id: string;
  name: string;
  genres: string[];
  popularity: number;
  images: { url: string }[];
}

interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  image_url: string;
}

export default function TopArtists() {
  const [topArtists, setTopArtists] = useState<Artist[]>([]);
  const [topTracks, setTopTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isArtists, setIsArtists] = useState(true);

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
        console.log(response.top_artists);
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
    const fetchTopTracks = async () => {
      try {
        const response = await get<{ tracks: Track[] }>(
          "/api/user-top-tracks/"
        );
        setTopTracks(response.tracks);
        setLoading(false);
      } catch (err) {
        console.error(err);
        if (err instanceof Error) {
          setError(`Failed to fetch top tracks: ${err.message}`);
        } else {
          setError("An unexpected error occurred");
        }
        setLoading(false);
      }
    };

    fetchTopTracks();
    fetchTopArtists();
  }, []);

  function toggle() {
    setIsArtists(!isArtists);
  }
  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div>
      <ul className="flex flex-wrap gap-8 justify-center">
        {isArtists &&
          topArtists.map((artist, index) => (
            <li
              key={artist.id}
              style={{ backgroundImage: `url(${artist.images[0].url})` }}
              className="bg-white shadow-md rounded-lg p-4 bg-cover bg-center h-64 w-64 relative"
            >
              <h3 className="font-bold text-lg bg-white/80 rounded-full text-center">
                {artist.name}
              </h3>

              {index === 0 && (
                <h2 className="text-2xl lg:text-3xl text-bold text-white absolute top-[-2rem] w-[800px] lg:top-[-6rem]">
                  Your Top
                  <span
                    className="bg-gray-300 rounded-lg ml-2 p-1"
                    onClick={toggle}
                  >
                    <span
                      className={
                        isArtists
                          ? "bg-white rounded-lg text-black px-6"
                          : "text-gray-700 px-6"
                      }
                    >
                      Artists
                    </span>
                    <span
                      className={
                        isArtists
                          ? "text-gray-700 px-6"
                          : "bg-white rounded-lg text-black px-6"
                      }
                    >
                      Songs
                    </span>
                  </span>
                </h2>
              )}
            </li>
          ))}

        {!isArtists &&
          topTracks.map((track, index) => (
            <>
              <li
                key={track.id}
                style={{ backgroundImage: `url(${track.image_url})` }}
                className="bg-white shadow-md rounded-lg p-4 bg-cover bg-center h-64 w-64 relative"
              >
                <h3 className="font-regular text-base bg-white/80 rounded-full text-center p-2">
                  {track.name}
                </h3>

                <h3 className="font-bold text-lg bg-white/80 rounded-full text-center mt-2">
                  {track.artist}
                </h3>

                {index === 0 && (
                  <h2 className="text-2xl lg:text-3xl text-bold text-white absolute top-[-2rem] w-[800px] lg:top-[-6rem]">
                    Your Top
                    <span
                      className="bg-gray-300 rounded-lg ml-2 p-1"
                      onClick={toggle}
                    >
                      <span
                        className={
                          isArtists
                            ? "bg-white rounded-lg text-black px-6"
                            : "text-gray-700 px-6"
                        }
                      >
                        Artists
                      </span>
                      <span
                        className={
                          isArtists
                            ? "text-gray-700 px-6"
                            : "bg-white rounded-lg text-black px-6"
                        }
                      >
                        Songs
                      </span>
                    </span>
                  </h2>
                )}
              </li>
            </>
          ))}
      </ul>
    </div>
  );
}
