import Image from "next/image";
import Link from "next/link";

export default function Home() {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  return (
    <main className="bg-stone-950 h-screen max-w-[1300px] flex items-center justify-around p-4 gap-8 text-white mx-auto">
      <section className="p-8 w-[50%] flex justify-center">
        <div className=" p-4 flex gap-16 flex-col">
          <h1 className="text-5xl capitalize leading-tight font-bold">
            find your next favorite song
          </h1>
          <p className="m-2 leading-relaxed text-xl font-light">
            SongScope uses advanced algorithms to find songs you’re likely to
            really enjoy.
          </p>
          <div className="flex">
            <Link
              href={`${backendUrl}/spotify-login`}
              className="bg-green text-black font-bold rounded-full py-3 px-8 flex items-center justify-center m-3 hover:scale-105  transition-transform duration-200"
            >
              <span className="pr-2">Login with Spotify</span>
              <Image
                src="/images/spotify-logo.png" // path relative to the public folder
                alt="collage of album art"
                width= "20"
                height="20" 
                priority
              />
            </Link>
          </div>
        </div>
      </section>
      <section className="border-2 border-black w-[50%] relative min-h-[90%]">
        <Image
          src="/images/albums.png" // path relative to the public folder
          alt="collage of album art"
          layout="fill" // This makes the image fill the parent container
          objectFit="cover"
          priority
        />
      </section>
    </main>
  );
}
