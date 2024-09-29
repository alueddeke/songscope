import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

const UserProfile = () => {
  const [topTracks, setTopTracks] = useState([]);
  const [error, setError] = useState(null);
  const router = useRouter();

  useEffect(() => {
    const fetchTopTracks = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/user-top-tracks/`, {
          credentials: 'include',
        });
        if (!response.ok) {
          throw new Error('Failed to fetch top tracks');
        }
        const data = await response.json();
        setTopTracks(data.items);
      } catch (err) {
        setError(err.message);
      }
    };

    fetchTopTracks();
  }, []);

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Your Top 10 Tracks</h1>
      {topTracks.length > 0 ? (
        <ul className="space-y-2">
          {topTracks.map((track, index) => (
            <li key={track.id} className="bg-gray-100 p-2 rounded">
              {index + 1}. {track.name} by {track.artists.map(artist => artist.name).join(', ')}
            </li>
          ))}
        </ul>
      ) : (
        <p>Loading your top tracks...</p>
      )}
    </div>
  );
};

export default UserProfile;