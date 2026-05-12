"use client";

import { useState, useEffect } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { get } from "../../../../services/axios";

interface TrendPoint {
  date: string;
  like_rate: number;
}

interface TrendResponse {
  data: TrendPoint[];
  message?: string;
}

export default function LikeTrendChart() {
  const [data, setData] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get<TrendResponse>("/api/recommendation-trend/")
      .then((r) => setData(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
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

  if (data.length < 2) {
    return (
      <p className="text-gray-400 text-sm text-center py-8">
        Not enough data yet — your like-rate trend will appear after a few days of gems.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid stroke="#374151" />
        <XAxis
          dataKey="date"
          tickFormatter={(d: string) =>
            new Date(d).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            })
          }
          tick={{ fill: "#6b7280", fontSize: 12 }}
        />
        <YAxis domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 12 }} />
        <Tooltip
          formatter={(v) => (v != null ? `${v}%` : "")}
          contentStyle={{ background: "#111827", border: "1px solid #374151" }}
          itemStyle={{ color: "#f3f4f6" }}
        />
        <Line
          type="monotone"
          dataKey="like_rate"
          stroke="#1DB954"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
