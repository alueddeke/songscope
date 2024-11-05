'use client'
import { post } from "@/services/axios"

interface AddToLikedProps{
    id: string
}

export function AddToLiked(props: AddToLikedProps){

    const track_id = props.id

    async function addToSpotify(){
        console.log("adding to spotify")
        try{
            const response: Response = await post("http://localhost:8000/api/add-track-to-liked/", {track_id: track_id});
            console.log(response)
        }catch{
            console.log("error adding to liked")
        }
    }

    return(
        <button onClick={addToSpotify} className="bg-green rounded-full flex-1 text-black py-2 hover:scale-105  transition-transform duration-200">Add to Liked</button>
    )
}

