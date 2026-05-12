"use client";

import { useState, useEffect } from "react";
import { get } from "../../../../services/axios";

interface Metrics {
  total_recommended: number;
  avg_popularity: number;
  novel_track_rate: number;
  hidden_gem_rate: number;
  gem_total: number;
  gem_liked: number;
  gem_disliked: number;
  gem_acceptance_rate: number | null;
  top_genres: string[];
  message?: string;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 min-w-[100px]">
      <span className="text-green text-lg font-bold tabular-nums">{value}</span>
      <span className="text-gray-500 text-xs uppercase tracking-widest">{label}</span>
    </div>
  );
}

export default function MetricsStrip() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMetrics = async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    try {
      const data = await get<Metrics>("/api/recommendation-metrics/");
      setMetrics(data);
    } catch {
      // silently ignore — strip is informational
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  if (loading || !metrics || metrics.message) return null;

  const acceptance =
    metrics.gem_acceptance_rate !== null
      ? `${Math.round(metrics.gem_acceptance_rate * 100)}%`
      : "—";

  return (
    <div className="w-full border-t border-gray-800 py-6 px-4 md:px-8 lg:px-16">
      <div className="flex flex-wrap gap-8 items-start justify-between">
        <div className="flex flex-wrap gap-8">
          <Stat label="Gems shown" value={String(metrics.gem_total)} />
          <Stat label="Gems liked" value={String(metrics.gem_liked)} />
          <Stat label="Acceptance rate" value={acceptance} />
          <Stat label="Avg popularity" value={`${metrics.avg_popularity}/100`} />
          <Stat label="Hidden gem rate" value={`${Math.round(metrics.hidden_gem_rate * 100)}%`} />
        </div>

        {metrics.top_genres.length > 0 && (
          <div className="flex flex-col gap-1">
            <span className="text-gray-500 text-xs uppercase tracking-widest">Top genres</span>
            <div className="flex flex-wrap gap-1.5">
              {metrics.top_genres.map((g) => (
                <span
                  key={g}
                  className="text-xs bg-gray-900 border border-gray-700 text-gray-300 px-2.5 py-0.5 rounded-full"
                >
                  {g}
                </span>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={() => fetchMetrics(true)}
          disabled={refreshing}
          className="text-gray-600 text-xs hover:text-gray-400 transition-colors self-start mt-1"
        >
          {refreshing ? "Refreshing…" : "Refresh stats"}
        </button>
      </div>
    </div>
  );
}
