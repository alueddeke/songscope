import React, { useEffect, useState } from "react";

const UserPlaylists = () => {
  const [playlists, setPlaylists] = useState([]);

  useEffect(() => {
    const fetchPlaylists = async () => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/user-playlists/`
      );
      const data = await response.json();
      setPlaylists(data.items);
    };
    fetchPlaylists();
  }, []);

  return (
    <div>
      <h2>Your Playlists</h2>
      <ul>
        {playlists.map((playlist) => (
          <li key={playlist.id}>{playlist.name}</li>
        ))}
      </ul>
    </div>
  );
};

export default UserPlaylists;
