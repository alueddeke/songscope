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
import UserMenu from './components/UserMenu/UserMenu'
import DemoBanner from '../components/DemoBanner'

async function getUserName() {
  // Demo mode: no per-user login — the backend resolves the seeded demo user,
  // so skip the session-cookie gate entirely.
  const isDemo = process.env.NEXT_PUBLIC_DEMO_MODE === 'true'
  const cookieStore = cookies()
  const sessionCookie = cookieStore.get('sessionid')

  if (!isDemo && !sessionCookie) {
    redirect('/') // or your login page
  }

  // In demo mode the backend (free Render tier) may be cold and take 30-50s to
  // wake. Never let that block the page: fail fast, render with a fallback name,
  // and let the client child components load data (with their own spinners)
  // once the backend is awake. This avoids a cold-start 502 on the whole page.
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), isDemo ? 8000 : 30000)
    const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/get-user-name/`, {
      headers: sessionCookie ? { 'Cookie': `sessionid=${sessionCookie.value}` } : {},
      cache: 'no-store',
      signal: controller.signal,
    }).finally(() => clearTimeout(timeout))

    if (!isDemo && (response.status === 401 || response.status === 403)) {
      redirect('/')
    }
    if (!response.ok) {
      if (isDemo) return 'there'
      throw new Error('Failed to fetch user data')
    }

    const data = await response.json()
    return data.user_name?.display_name ?? 'there'
  } catch (err) {
    if (isDemo) return 'there' // cold backend / timeout — render anyway
    throw err
  }
}

const UserProfile = async () => {
  const userName = await getUserName()

  return (
    <div className="w-[100%] max-w-[1300px] mx-auto">
      <DemoBanner />
      <UserMenu />
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
            <p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Your genre taste profile</p>
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
