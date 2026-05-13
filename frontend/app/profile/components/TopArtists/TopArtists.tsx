'use client';

import { useState, useEffect } from 'react';
import { TrendingUp } from 'lucide-react';
import { get } from '@/services/axios';
import ArtistExpandedDetails, { ArtistDetailsData } from './ArtistExpandedDetails';

interface Artist {
  id: string;
  name: string;
  images: Array<{ url: string }>;
  popularity: number;
  genres: string[];
}

interface TopArtistsResponse {
  top_artists: Artist[];
  time_range: string;
  total_count: number;
}

type TimeRange = '4 weeks' | '6 months' | 'year';

interface TopArtistsProps {
  timeRange?: TimeRange;
}

const TIME_RANGE_LABELS = {
  '4 weeks': 'Last 4 Weeks',
  '6 months': 'Last 6 Months', 
  'year': 'Last 12 Months'
};

const getArtistImage = (artist: Artist): string => {
  return artist.images?.[0]?.url || '/images/albums.png';
};

const getPopularityColor = (popularity: number): string => {
  if (popularity >= 80) return 'text-green-400';
  if (popularity >= 60) return 'text-yellow-400';
  if (popularity >= 40) return 'text-orange-400';
  return 'text-red-400';
};

export default function TopArtists({ timeRange = '4 weeks' as TimeRange }: TopArtistsProps) {
  const [artists, setArtists] = useState<Artist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedArtistId, setExpandedArtistId] = useState<string | null>(null);
  const [expandedArtistData, setExpandedArtistData] = useState<ArtistDetailsData | null>(null);
  const [loadingArtistDetails, setLoadingArtistDetails] = useState(false);

  useEffect(() => {
    fetchTopArtists();
  }, [timeRange]);

  const fetchTopArtists = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await get<TopArtistsResponse>(`/api/user-top-artists/?time_range=${timeRange}`);
      setArtists(data.top_artists || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleArtistClick = async (artistId: string) => {
    if (expandedArtistId === artistId) {
      // Collapse if clicking the same artist
      setExpandedArtistId(null);
      setExpandedArtistData(null);
      return;
    }

    setExpandedArtistId(artistId);
    setLoadingArtistDetails(true);
    setExpandedArtistData(null);

    try {
      const data = await get(`/api/artist-details/${artistId}/`);
      console.log('Artist details response:', data);
      setExpandedArtistData(data);
    } catch (err) {
      console.error('Error fetching artist details:', err);
      setExpandedArtistData(null);
    } finally {
      setLoadingArtistDetails(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="text-center py-8">
          <div className="text-white text-sm mb-2">Loading top artists...</div>
          <div className="text-gray-400 text-xs">This may take a moment</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="text-center py-8">
          <div className="text-red-400 text-sm mb-2">Error loading top artists</div>
          <div className="text-gray-400 text-xs">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Top Artists</h2>
        <div className="text-sm text-gray-400">
          {TIME_RANGE_LABELS[timeRange as keyof typeof TIME_RANGE_LABELS]}
        </div>
      </div>

      {/* Artists Grid with Dynamic Expansion */}
      {artists.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-gray-400 text-sm">No top artists found</div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Artists Grid with Dynamic Expansion */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {(() => {
              // Create a flattened array of grid items with expanded row insertion
              const gridItems: JSX.Element[] = [];
              
              artists.forEach((artist, index) => {
                // Add the artist card
                gridItems.push(
                  <div
                    key={artist.id}
                    onClick={() => handleArtistClick(artist.id)}
                    className="bg-gray-800 rounded-lg p-4 hover:bg-gray-750 transition-all duration-300 cursor-pointer group"
                  >
                    {/* Artist Image */}
                    <div className="relative mb-3">
                      <img
                        src={getArtistImage(artist)}
                        alt={artist.name}
                        className="w-full h-24 object-cover rounded-lg transition-transform duration-300 group-hover:scale-105"
                        onError={(e) => {
                          e.currentTarget.src = '/images/albums.png';
                        }}
                      />
                      {/* Popularity Badge */}
                      <div className="absolute top-2 right-2 bg-black/70 rounded-full px-2 py-1">
                        <TrendingUp className={`w-3 h-3 ${getPopularityColor(artist.popularity)}`} />
                      </div>
                      {/* Rank Badge */}
                      <div className="absolute top-2 left-2 bg-green text-black rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">
                        {index + 1}
                      </div>
                    </div>

                    {/* Artist Info */}
                    <div className="text-center">
                      <h4 className="text-white font-medium text-sm mb-1 truncate group-hover:text-green transition-colors">
                        {artist.name}
                      </h4>
                      <div className="text-xs text-gray-400">
                        {artist.genres.slice(0, 2).join(', ')}
                      </div>
                      <div className={`text-xs mt-1 ${getPopularityColor(artist.popularity)}`}>
                        {artist.popularity}% popular
                      </div>
                    </div>
                  </div>
                );

                // If this is the expanded artist, insert the expanded details after it
                if (expandedArtistId === artist.id) {
                  gridItems.push(
                    <div
                      key={`expanded-${artist.id}`}
                      className={`overflow-hidden transition-all duration-500 ease-in-out col-span-full ${
                        expandedArtistId ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'
                      }`}
                    >
                      <div className="bg-gray-850 rounded-lg p-6 border border-gray-700 w-full">
                        {loadingArtistDetails ? (
                          <div className="text-center py-8">
                            <div className="text-white text-sm mb-2">Loading artist details...</div>
                            <div className="text-gray-400 text-xs">This may take a moment</div>
                          </div>
                        ) : expandedArtistData ? (
                          <ArtistExpandedDetails 
                            artist={expandedArtistData} 
                            loading={false} 
                          />
                        ) : (
                          <div className="text-center py-8">
                            <div className="text-red-400 text-sm">Failed to load artist details</div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                }
              });

              return gridItems;
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
