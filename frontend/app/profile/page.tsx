import { cookies } from 'next/headers'
import Image from 'next/image'
import { redirect } from 'next/navigation'
import Recommendation from './components/Recommendation/Recommendation'

async function getUserName() {
  const cookieStore = cookies()
  // Get your Django session cookie - you'll need to check the exact name
  // It's often something like 'sessionid' or 'csrftoken'
  const sessionCookie = cookieStore.get('sessionid')
  
  if (!sessionCookie) {
    redirect('/') // or your login page
  }

  const response = await fetch('http://localhost:8000/api/get-user-name/', {
    headers: {
      'Cookie': `sessionid=${sessionCookie.value}`,
      // If you're using CSRF protection, include that token too
      // 'X-CSRFToken': csrfCookie.value
    },
    // Prevent caching since this is user-specific data
    cache: 'no-store'
  })

  if (!response.ok) {
    // Handle various error cases
    if (response.status === 404) {
      redirect('/') // Token not found, redirect to login
    }
    throw new Error('Failed to fetch user data')
  }

  const data = await response.json()
  return data.user_name.display_name
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

      <section className="min-h-[100vh] flex justify-center items-center">
        <Recommendation />
      </section>
    </div>
  );
};

export default UserProfile;
