"use client";
import React from "react";
import H5AudioPlayer from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css"

interface AudioPlayerProps {
  src: string;
}

export function AudioPlayer(props: AudioPlayerProps) {
  const src = props.src;
  return (
    <H5AudioPlayer
      
      className="rounded-sm"
      style={{
        backgroundColor: "black",
        color: "white",
        accentColor: "white",
        padding: "1rem 2rem",
        borderRadius: "4px",
      }}
      showSkipControls={false}
      showJumpControls={false}
      loop={false}
      autoPlay={false}
      preload="metadata"
      src={src}
      autoPlayAfterSrcChange={false}
    />
  );
}
