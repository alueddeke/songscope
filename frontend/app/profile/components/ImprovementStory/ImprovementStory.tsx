"use client";

import { useState, useEffect } from "react";
import { get } from "../../../../services/axios";

interface Story {
  first_7_rate: number | null;
  last_7_rate: number | null;
  delta: number | null;
}

interface MetricsResponse {
  improvement_story?: Story;
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

export default function ImprovementStory() {
  const [story, setStory] = useState<Story | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get<MetricsResponse>("/api/recommendation-metrics/")
      .then((r) => setStory(r.improvement_story ?? null))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading || !story || story.first_7_rate === null || story.last_7_rate === null) {
    return null;
  }

  const delta = story.delta;
  let deltaClass = "text-gray-500 text-xs";
  let deltaText = "— 0pp";

  if (delta !== null && delta > 0) {
    deltaClass = "text-green text-xs";
    deltaText = `▲ +${delta}pp`;
  } else if (delta !== null && delta < 0) {
    deltaClass = "text-red-400 text-xs";
    deltaText = `▼ ${delta}pp`;
  }

  return (
    <div className="flex items-end gap-6">
      <Stat label="When I started" value={`${story.first_7_rate}%`} />
      <Stat label="Now" value={`${story.last_7_rate}%`} />
      <span className={deltaClass}>{deltaText}</span>
    </div>
  );
}
