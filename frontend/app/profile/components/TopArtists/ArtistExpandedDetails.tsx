'use client';

import { TrendingUp, ExternalLink, Calendar, Music, Play } from 'lucide-react';

interface Track {
  id: string;
  name: string;
  album: string;
  image?: string;
  preview_url?: string;
  external_urls: { spotify: string };
  source: 'top_tracks' | 'recent_tracks' | 'liked_songs' | 'artist_albums';
}

interface Album {
  id: string;
  name: string;
  image?: string;
  release_date: string;
  type: string;
  total_tracks: number;
}

export interface ArtistDetailsData {
  id: string;
  name: string;
  images: Array<{ url: string }>;
  followers: number;  // Backend returns this as a number directly
  popularity: number;
  genres: string[];
  external_urls: { spotify: string };
  latest_album?: Album;
  user_top_tracks: Track[];
  top_tracks: Track[];
}

interface ArtistExpandedDetailsProps {
  artist: ArtistDetailsData | null;
  loading: boolean;
}

const getArtistImage = (artist: ArtistDetailsData): string => {
  return artist.images?.[0]?.url || '/images/albums.png';
};

const formatFollowers = (followers: number | undefined): string => {
  if (!followers || isNaN(followers)) {
    return '0';
  }
  
  if (followers >= 1000000) {
    return `${(followers / 1000000).toFixed(1)}M`;
  } else if (followers >= 1000) {
    return `${(followers / 1000).toFixed(1)}K`;
  }
  return followers.toString();
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  });
};

export default function ArtistExpandedDetails({ artist, loading }: ArtistExpandedDetailsProps) {
  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="text-white text-sm mb-2">Loading artist details...</div>
        <div className="text-gray-400 text-xs">This may take a moment</div>
      </div>
    );
  }

  if (!artist) {
    return (
      <div className="text-center py-8">
        <div className="text-red-400 text-sm">Failed to load artist details</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Row 1: Artist Info, Spotify Link, Latest Release */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Artist Info with Image and Stats */}
        <div className="flex flex-col md:flex-row lg:flex-col gap-4">
          {/* Large Artist Image */}
          <div className="flex-shrink-0">
            <img
              src={getArtistImage(artist)}
              alt={artist.name}
              className="w-48 h-48 object-cover rounded-lg shadow-lg"
              onError={(e) => {
                e.currentTarget.src = '/images/albums.png';
              }}
            />
          </div>

          {/* Artist Stats */}
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-gray-400">
                <TrendingUp className="w-4 h-4" />
                <span>{formatFollowers(artist.followers)} followers</span>
              </div>
              <div className="flex items-center gap-2 text-gray-400">
                <TrendingUp className="w-4 h-4" />
                <span>{artist.popularity || 0}% popular</span>
              </div>
            </div>

            {/* Genres */}
            <div>
              <h3 className="text-green font-medium mb-2">Genres</h3>
              <div className="flex flex-wrap gap-2">
                {(artist.genres || []).slice(0, 5).map((genre, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-gray-800 text-gray-300 rounded-full text-sm"
                  >
                    {genre}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Spotify Link */}
        {artist.external_urls.spotify && (
          <div className="flex flex-col items-center justify-center">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <ExternalLink className="w-5 h-5 text-green" />
              Connect
            </h3>
            <a
              href={artist.external_urls.spotify}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-green text-black rounded-lg hover:bg-green-600 transition-colors font-medium"
            >
              <ExternalLink className="w-5 h-5" />
              Open in Spotify
            </a>
          </div>
        )}

        {/* Latest Release */}
        {artist.latest_album && (
          <div className="flex flex-col items-center">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-green" />
              Latest Release
            </h3>
            <div className="bg-gray-800 rounded-lg p-4 hover:bg-gray-750 transition-colors text-center">
              <img
                src={artist.latest_album.image || '/images/albums.png'}
                alt={artist.latest_album.name}
                className="w-32 h-32 object-cover rounded mb-3 mx-auto"
              />
              <div className="text-white font-medium text-sm mb-1 truncate">{artist.latest_album.name}</div>
              <div className="text-gray-400 text-xs">
                {artist.latest_album.type.charAt(0).toUpperCase() + artist.latest_album.type.slice(1)} • {formatDate(artist.latest_album.release_date)}
              </div>
              <div className="text-gray-500 text-xs">{artist.latest_album.total_tracks} tracks</div>
            </div>
          </div>
        )}
      </div>

      {/* Row 2: Your Favorite Tracks and Most Popular Tracks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Your Favorite Tracks */}
        {(artist.user_top_tracks || []).length > 0 ? (
          <div>
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Music className="w-5 h-5 text-green" />
              {(() => {
                const hasTopTracks = artist.user_top_tracks.some(track => track.source === 'top_tracks');
                const hasRecentTracks = artist.user_top_tracks.some(track => track.source === 'recent_tracks');
                const hasLikedSongs = artist.user_top_tracks.some(track => track.source === 'liked_songs');
                const allFromAlbums = artist.user_top_tracks.every(track => track.source === 'artist_albums');
                
                if (allFromAlbums) {
                  return "We think you would like these";
                } else if (hasTopTracks || hasRecentTracks || hasLikedSongs) {
                  return "Your Favorite Tracks";
                } else {
                  return "We think you would like these";
                }
              })()}
            </h3>
            <div className="space-y-2">
              {artist.user_top_tracks.map((track, index) => {
                const hasTopTracks = artist.user_top_tracks.some(track => track.source === 'top_tracks');
                const hasRecentTracks = artist.user_top_tracks.some(track => track.source === 'recent_tracks');
                const hasLikedSongs = artist.user_top_tracks.some(track => track.source === 'liked_songs');
                const allFromAlbums = artist.user_top_tracks.every(track => track.source === 'artist_albums');
                const showAlbumText = !allFromAlbums; // Only show blue text if NOT all from albums
                
                return (
                  <a
                    key={track.id}
                    href={track.external_urls.spotify}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-750 transition-colors cursor-pointer group"
                  >
                    <div className="relative">
                      <img
                        src={track.image || '/images/albums.png'}
                        alt={track.album}
                        className="w-12 h-12 object-cover rounded"
                      />
                      <div className="absolute inset-0 bg-black/50 rounded flex items-center justify-center">
                        <span className="text-white text-xs font-bold">{index + 1}</span>
                      </div>
                      {track.source === 'artist_albums' && showAlbumText && (
                        <div className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs px-1 rounded">
                          *
                        </div>
                      )}
                      {track.source === 'top_tracks' && (
                        <div className="absolute -top-1 -right-1 bg-green-500 text-white text-xs px-1 rounded">
                          ♥
                        </div>
                      )}
                      {track.source === 'liked_songs' && (
                        <div className="absolute -top-1 -right-1 bg-red-500 text-white text-xs px-1 rounded">
                          ❤
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-white font-medium text-sm truncate group-hover:text-green transition-colors">{track.name}</div>
                      <div className="text-gray-400 text-xs truncate">{track.album}</div>
                      {track.source === 'artist_albums' && showAlbumText && (
                        <div className="text-blue-400 text-xs">We think you would like this</div>
                      )}
                      {track.source === 'top_tracks' && (
                        <div className="text-green-400 text-xs">In your top tracks</div>
                      )}
                      {track.source === 'recent_tracks' && (
                        <div className="text-yellow-400 text-xs">Recently played</div>
                      )}
                      {track.source === 'liked_songs' && (
                        <div className="text-green-400 text-xs">In your liked songs</div>
                      )}
                    </div>
                    <div className="text-gray-500 group-hover:text-green transition-colors">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </div>
                  </a>
                );
              })}
            </div>
          </div>
        ) : (
          <div>
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Music className="w-5 h-5 text-green" />
              We think you would like these
            </h3>
            <div className="text-center py-8">
              <div className="text-gray-400 text-sm">No tracks available for this artist</div>
              <div className="text-gray-500 text-xs mt-1">Try listening to their music!</div>
            </div>
          </div>
        )}

        {/* Most Popular Tracks */}
        {(artist.top_tracks || []).length > 0 && (
          <div>
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Play className="w-5 h-5 text-green" />
              Most Popular Tracks
            </h3>
            <div className="space-y-2">
              {artist.top_tracks.map((track, index) => (
                <a
                  key={track.id}
                  href={track.external_urls.spotify}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-750 transition-colors cursor-pointer group"
                >
                  <div className="w-8 h-8 bg-green text-black rounded-full flex items-center justify-center text-sm font-bold">
                    {index + 1}
                  </div>
                  <img
                    src={track.image || '/images/albums.png'}
                    alt={track.album}
                    className="w-12 h-12 object-cover rounded"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-white font-medium text-sm truncate group-hover:text-green transition-colors">{track.name}</div>
                    <div className="text-gray-400 text-xs truncate">{track.album}</div>
                  </div>
                  {track.preview_url && (
                    <button className="p-2 text-gray-400 hover:text-green transition-colors">
                      <Play className="w-4 h-4" />
                    </button>
                  )}
                  <div className="text-gray-500 group-hover:text-green transition-colors">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 