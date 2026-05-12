"use client";

import { useState, useEffect } from "react";
import { get } from "../../../../services/axios";

interface MetricsResponse {
  diversity_score?: number | null;
  message?: string;
}

export default function DiversityScore() {
  const [score, setScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get<MetricsResponse>("/api/recommendation-metrics/")
      .then((r) => setScore(r.diversity_score ?? null))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return null;
  }

  const displayValue =
    score !== null ? `${(score * 100).toFixed(0)}%` : "—";

  return (
    <div
      className="flex flex-col gap-0.5 min-w-[100px]"
      title="How different your recommended tracks have been from each other. 100% = every track from a completely different genre."
    >
      <span className="text-green text-lg font-bold tabular-nums">{displayValue}</span>
      <span className="text-gray-500 text-xs uppercase tracking-widest">Genre diversity</span>
    </div>
  );
}
