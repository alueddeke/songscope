"use client";

interface ScoreBreakdownProps {
  breakdown: Record<string, number>;
}

const SCORE_ROWS: { key: string; label: string }[] = [
  { key: "genre_sim",           label: "Genre Match" },
  { key: "novelty",             label: "Novelty"     },
  { key: "feedback_multiplier", label: "Feedback"    },
];

export default function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  if (Object.keys(breakdown).length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      {SCORE_ROWS.map(({ key, label }) => {
        const raw = breakdown[key] ?? 0;
        const pct = Math.round(raw * 100 / 5) * 5;
        return (
          <div key={key} className="flex items-center gap-2">
            <span className="text-sm text-gray-300 w-28 flex-shrink-0">{label}</span>
            <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
              <div className="bg-green rounded-full h-full" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-sm font-bold text-gray-300 w-9 text-right flex-shrink-0">{pct}%</span>
          </div>
        );
      })}
    </div>
  );
}
