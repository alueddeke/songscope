// Demo-mode notice. Renders only when NEXT_PUBLIC_DEMO_MODE === 'true'.
// Sets honest expectations: the public demo is backed by one shared Spotify
// account, whereas production SongScope personalizes per user.
export default function DemoBanner() {
  if (process.env.NEXT_PUBLIC_DEMO_MODE !== 'true') return null;
  return (
    <div className="w-full bg-stone-900 border-b border-green/30 text-green text-xs sm:text-sm px-4 py-3 text-center leading-relaxed">
      <span className="font-bold">Demo mode</span> — SongScope is connected to a
      single Spotify account, learning from one person&apos;s listening history.
      In production it tailors recommendations to each user&apos;s own listening
      patterns; this shared demo can&apos;t personalize per visitor.
    </div>
  );
}
