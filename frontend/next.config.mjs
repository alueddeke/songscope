import dotenv from "dotenv";
dotenv.config({ path: "../.env" }); // Load shared environment variables
dotenv.config({ path: "./.env.local" }); // Load local environment variables

// console.log("Environment Variables:", {
//   SPOTIFY_CLIENT_ID: process.env.SPOTIFY_CLIENT_ID,
//   SPOTIFY_CLIENT_SECRET: process.env.SPOTIFY_CLIENT_SECRET,
//   REDIRECT_URI: process.env.REDIRECT_URI,
//   NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,

// });

/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    SPOTIFY_CLIENT_ID: process.env.SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET: process.env.SPOTIFY_CLIENT_SECRET,
    REDIRECT_URI: process.env.REDIRECT_URI,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
  },
};

export default nextConfig;
