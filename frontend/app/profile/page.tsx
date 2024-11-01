"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import RecentlyPlayed from "./components/RecentlyPlayed/RecentlyPlayed";
import Recommendations from "./components/Recommendations/Recommendations";
import Recommendation from "./components/Recommendation/Recommendation";
import TopArtists from "./components/TopArtists/TopArtists";
import TopTracks from "./components/TopTracks/TopTracks";
import { get } from "../../services/axios";

const UserProfile = () => {
  const [userName, setUserName] = useState("");

  useEffect(() => {
    async function getUserName() {
      try {
        const response = await get("/api/get-user-name/");
        console.log(response);
        const username = response.user_name.display_name;
        setUserName(username);
      } catch (err) {
        console.log(err);
      }
    }
    getUserName();
  }, []);

  return (
    <div className=" w-[100%] max-w-[1300px] mx-auto">
      <section className="min-h-screen flex flex-col justify-center gap-8 p-16 relative">
        <div className="pb-16">
          <h1 className="text-green text-5xl">Welcome back, {userName}.</h1>
          <h2 className="text-white mt-16 text-xl">
            We scoped out a song we think you might like.
          </h2>
        </div>
        <Image
          src="/images/arrow_back.png" // path relative to the public folder
          alt="collage of album art"
          width="70"
          height="70"
          priority
          className="absolute bottom-16"
        />
      </section>

      <section className="min-h-[100vh] flex justify-center items-center">
        <Recommendation />
      </section>

      {/* <h1>This is your Spotify Profile</h1>

      <TopTracks />
      <div className="mt-8">
        <Recommendations />
      </div>
      <div className="mt-8">
        <RecentlyPlayed />
      </div>
      <div className="mt-8">
        <TopArtists />
      </div> */}
    </div>
  );
};

export default UserProfile;
