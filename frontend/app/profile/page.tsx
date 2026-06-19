import { cookies } from 'next/headers'
import Image from 'next/image'
import { redirect } from 'next/navigation'
import DailyGem from './components/DailyGem/DailyGem'
import TopArtists from './components/TopArtists/TopArtists'
import MetricsStrip from './components/MetricsStrip/MetricsStrip'
import LikeTrendChart from './components/LikeTrendChart/LikeTrendChart'
import TasteProfileChart from './components/TasteProfileChart/TasteProfileChart'
import DiversityScore from './components/DiversityScore/DiversityScore'
import ImprovementStory from './components/ImprovementStory/ImprovementStory'

async function getUserName() {
  const cookieStore = cookies()
  // Get your Django session cookie - you'll need to check the exact name
  // It's often something like 'sessionid' or 'csrftoken'
  const sessionCookie = cookieStore.get('sessionid')

  if (!sessionCookie) {
    redirect('/') // or your login page
  }

          const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/get-user-name/`, {
    headers: {
      'Cookie': `sessionid=${sessionCookie.value}`,
      // If you're using CSRF protection, include that token too
      // 'X-CSRFToken': csrfCookie.value
    },
    // Prevent caching since this is user-specific data
    cache: 'no-store'
  })

  if (response.status === 401 || response.status === 403) {
    redirect('/')
  }
  if (!response.ok) {
    throw new Error('Failed to fetch user data')
  }

  const data = await response.json()
  return data.user_name?.display_name ?? 'there'
}

const UserProfile = async () => {
  const userName = await getUserName()

  return (
    <div className=" w-[100%] max-w-[1300px] mx-auto">
      <section className="min-h-screen flex flex-col justify-center gap-8 p-2 md:p-8 lg:p-16 relative text-center md:text-left">
        <div className="pb-16">
          <h1 className="text-green text-5xl">Welcome back, {userName}.</h1>
          <h2 className="text-white mt-16 text-xl">
            We scoped out a song we think you might like.
          </h2>
        </div>
        <Image
          src="/images/arrow_back.png" // path relative to the public folder
          alt="down arrow icon"
          width="70"
          height="70"
          priority
          className="absolute bottom-16"
        />
      </section>

      <section className="min-h-[100vh] flex justify-center items-center p-2 md:p-8 lg:p-16">
        <DailyGem />
      </section>

      <section className="py-64">
        <TopArtists/>
      </section>

      <MetricsStrip />

      <section className="w-full border-t border-gray-800 py-16 px-4 md:px-8 lg:px-16">
        <h2 className="text-2xl font-bold text-white mb-8">How your taste is evolving</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Like-rate trend (7-day rolling)</p>
            <LikeTrendChart />
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Your taste profile</p>
            <TasteProfileChart />
          </div>
        </div>
        <div className="flex flex-wrap gap-8 mt-12 pt-8 border-t border-gray-800">
          <DiversityScore />
          <ImprovementStory />
        </div>
      </section>
    </div>
  );
};

export default UserProfile;
