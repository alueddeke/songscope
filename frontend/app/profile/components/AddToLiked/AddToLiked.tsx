"use client";
import { post } from "@/services/axios";
import { useState } from "react";

interface AddToLikedProps {
  id: string;
}

export function AddToLiked(props: AddToLikedProps) {
  const track_id = props.id;
  const [liked, setLiked] = useState<Boolean>(false)

  async function addToSpotify() {
    console.log("adding to spotify");
    setLiked(true)
    try {
      const response: Response = await post(
        "http://localhost:8000/api/add-track-to-liked/",
        { track_id: track_id }
      );
      console.log(response);
    } catch {
      console.log("error adding to liked");
    }
  }

  return (
    <button
      onClick={addToSpotify}
      className="bg-black border border-white rounded-full flex gap-2 items-center justify-center flex-1 text-black py-2 hover:scale-105  transition-transform duration-200"
    >
      <img className="w-5" src={liked ? "/icons/like-icon-liked.svg":"/icons/like-icon-like.svg" }/> 
      <span className="text-white">Add to Liked</span>
    </button>
  );
}
