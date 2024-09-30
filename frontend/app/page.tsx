import Image from "next/image";
import Link from "next/link";

export default function Home() {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  // console.log(backendUrl);
  return (
    <main className="bg-orange min-h-screen min-w-full flex items-center justify-around">
      <section className="border-2 border-black w-96 p-4">
        <h1 className="text-6xl">SongScope</h1>
        <p className="m-2">Learn how to find your next hidden gem</p>
        <div className="flex justify-end">
          <Link
            href={`${backendUrl}/spotify-login`}
            className="bg-dark text-white rounded-full w-28 h-28 flex items-center justify-center m-3 hover:scale-105  transition-transform duration-200"
          >
            Login
          </Link>
        </div>
      </section>
      <section className="border-2 border-black ">
        <div>this is an image</div>
      </section>
    </main>
  );
}
