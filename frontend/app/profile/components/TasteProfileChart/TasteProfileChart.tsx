"use client";

import { useState, useEffect } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { get } from "../../../../services/axios";

interface GenrePct {
  genre: string;
  pct: number;
}

interface MetricsResponse {
  top_genres_pct?: GenrePct[];
  message?: string;
}

export default function TasteProfileChart() {
  const [data, setData] = useState<GenrePct[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = () => {
    get<MetricsResponse>("/api/recommendation-metrics/")
      .then((r) => setData(r.top_genres_pct || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();

    const handler = () => setTimeout(fetchData, 500);
    window.addEventListener('songscope:feedback-action', handler);
    window.addEventListener('songscope:new-gem', handler);
    return () => {
      window.removeEventListener('songscope:feedback-action', handler);
      window.removeEventListener('songscope:new-gem', handler);
    };
  }, []);

  if (loading) {
    return (
      <div className="flex gap-1 justify-center py-8">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-2 h-2 rounded-full bg-green animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <p className="text-gray-400 text-sm text-center py-8">
        Your taste profile will appear once your listening history builds up.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart layout="vertical" data={data}>
        <XAxis
          type="number"
          domain={[0, 100]}
          tick={{ fill: "#6b7280", fontSize: 12 }}
        />
        <YAxis
          type="category"
          dataKey="genre"
          width={120}
          tick={{ fill: "#9ca3af", fontSize: 12 }}
        />
        <Tooltip
          formatter={(v) => (v != null ? `${v}%` : "")}
          contentStyle={{ background: "#111827", border: "1px solid #374151" }}
          itemStyle={{ color: "#f3f4f6" }}
        />
        <Bar dataKey="pct" fill="#1DB954" radius={[0, 3, 3, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
