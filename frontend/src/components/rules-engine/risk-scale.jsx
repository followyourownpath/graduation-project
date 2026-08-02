"use client";

import { riskDisplay } from "@/lib/risk-display";
import { cn } from "@/lib/utils";

const SCALE_NODES = [
  { score: 0, level: "low", label: "Low" },
  { score: 25, level: "lower", label: "Lower" },
  { score: 50, level: "medium", label: "Medium" },
  { score: 75, level: "higher", label: "Higher" },
  { score: 100, level: "high", label: "High" },
];

export function RiskScale({ score }) {
  return (
    <div className="w-full" role="img" aria-label={`Risk scale highlighting score ${score}`}>
      <div className="relative flex items-start justify-between">
        <div className="absolute left-0 right-0 top-3 h-1.5 rounded-full bg-slate-200" aria-hidden />
        {SCALE_NODES.map((node) => {
          const active = score === node.score;
          const display = riskDisplay(node.level);
          return (
            <div key={node.score} className="relative z-10 flex w-12 flex-col items-center gap-2">
              <span
                className={cn(
                  "flex h-6 w-6 items-center justify-center rounded-full border-2 text-[10px] font-bold transition-colors",
                  active ? "text-white shadow-sm" : "border-slate-300 bg-white text-slate-400",
                )}
                style={active ? { backgroundColor: display.ringColor, borderColor: display.ringColor } : undefined}
                aria-current={active ? "true" : undefined}
              >
                {node.score}
              </span>
              <span className={cn("text-xs font-medium", active ? "text-slate-900" : "text-slate-400")}>
                {node.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
