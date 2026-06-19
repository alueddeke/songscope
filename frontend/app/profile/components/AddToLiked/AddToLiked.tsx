"use client";
import { post } from "@/services/axios";
import { useState } from "react";

interface AddToLikedProps {
  id: string;
}

export function AddToLiked(props: AddToLikedProps) {
  const track_id = props.id;
  const [liked, setLiked] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  async function addToSpotify() {
    if (loading || liked) return;
    setLoading(true);
    try {
      await post<{ message: string }>("/api/add-track-to-liked/", { track_id });
      setLiked(true);
      window.dispatchEvent(new CustomEvent('songscope:feedback-action'));
    } catch (err) {
      console.error("Failed to add track to liked:", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={addToSpotify}
      disabled={loading || liked}
      className="bg-black border border-white rounded-full flex gap-2 items-center justify-center flex-1 text-black py-2 hover:scale-105 transition-transform duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <img className="w-5" src={liked ? "/icons/like-icon-liked.svg" : "/icons/like-icon-like.svg"} />
      <span className="text-white">{loading ? "Adding..." : "Add to Liked"}</span>
    </button>
  );
}
