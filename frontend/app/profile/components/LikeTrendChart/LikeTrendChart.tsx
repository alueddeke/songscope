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
  date?: string;
  label?: string; // demo mode: per-feedback sequence label (e.g. "#1")
  like_rate: number;
}

interface TrendResponse {
  data: TrendPoint[];
  message?: string;
}

export default function LikeTrendChart() {
  const [data, setData] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = () => {
    get<TrendResponse>("/api/recommendation-trend/")
      .then((r) => setData(r.data || []))
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

  // Demo mode returns a per-feedback sequence ({label, like_rate}); normal mode
  // returns a date series ({date, like_rate}).
  const isSequence = data.length > 0 && data[0].label !== undefined;

  if (data.length < 2) {
    return (
      <p className="text-gray-400 text-sm text-center py-8">
        Like or dislike a couple of gems and your taste trend will start moving here.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid stroke="#374151" />
        <XAxis
          dataKey={isSequence ? "label" : "date"}
          tickFormatter={
            isSequence
              ? (v: string) => v
              : (d: string) =>
                  new Date(d + "T00:00:00").toLocaleDateString("en-US", {
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
