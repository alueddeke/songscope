"use client";

import RecentlyPlayed from "./components/RecentlyPlayed/RecentlyPlayed";
import TopArtists from "./components/TopArtists/TopArtists";
import TopTracks from "./components/TopTracks/TopTracks";

const UserProfile = () => {
  return (
    <div className="container mx-auto p-4">
      <h1>This is your Spotify Profile</h1>

      <TopTracks />
      <div className="mt-8">
        <RecentlyPlayed />
      </div>
      <div className="mt-8">
        <TopArtists />
      </div>
    </div>
  );
};

export default UserProfile;
