import { AudioPlayer } from "../AudioPlayer/AudioPlayer";
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { AddToLiked } from "../AddToLiked/AddToLiked";
import FeedbackButtonGroup from "../Feedback/FeedbackButtonGroup";

interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  preview_url: string;
  image_url: string;
}

interface RecommendationsResponse {
  recommendations: Track[];
}

async function getRecommendations() {
  const cookieStore = cookies();
  // Get your Django session cookie - you'll need to check the exact name
  // It's often something like 'sessionid' or 'csrftoken'
  const sessionCookie = cookieStore.get("sessionid");

  if (!sessionCookie) {
    redirect("/"); // or your login page
  }

  const response: Response = await fetch("http://localhost:8000/api/recommendations/", {
    headers: {
      Cookie: `sessionid=${sessionCookie.value}`,
      // If you're using CSRF protection, include that token too
      // 'X-CSRFToken': csrfCookie.value
    },
    // Prevent caching since this is user-specific data
    cache: "no-store",
  });

  const data: RecommendationsResponse = await response.json()
  const recommendations = data.recommendations.filter(track => track.preview_url != null)

  if (!response.ok) {
    // Handle various error cases
    if (response.status === 404) {
      redirect("/"); // Token not found, redirect to login
    }
    throw new Error("Failed to fetch user data");
  }

  return recommendations
}

export default async function Recommendation() {
  const recommendations: Track[] = await getRecommendations()

  return (
    <div className="mx-auto flex gap-8 lg:gap-16 w-[100%] flex-col md:flex-row p-2 md:p-4 lg:p-8">
      <div className="md:w-[45%] lg:w-[55%] p-2 lg:p-0">
        <img src={recommendations[0].image_url} />
      </div>

      <div className="md:w-[55%] lg:w-[45%] flex flex-col gap-8 lg:gap-16 p-2 lg:p-0">
        <div className="flex flex-col gap-4">
          <h3 className="text-2xl lg:text-5xl text-bold text-white">
            {recommendations[0].name}
          </h3>
          <h4 className="text-xl text-bold text-white">
            {recommendations[0].artist}
          </h4>
          <h4 className="text-xl text-bold text-white">
            {recommendations[0].album}
          </h4>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-white font-light text-sm">preview</span>
          <AudioPlayer src={recommendations[0].preview_url}/>
        </div>

        <div className="flex gap-4 lg:gap-8 flex-col lg:flex-row">
          <AddToLiked id={recommendations[0].id}/>
          <a href={`https://open.spotify.com/track/${recommendations[0].id}`}
            className="bg-black rounded-full flex-1 text-white py-2 text-center hover:scale-105  transition-transform duration-200"
          >
            Open in Spotify
          </a>

          <FeedbackButtonGroup trackId={recommendations[0].id}/>
        </div>
      </div>
    </div>
  );
}
