"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RiskScale } from "@/components/rules-engine/risk-scale";
import { riskDisplay } from "@/lib/risk-display";

export function RiskScoreCard({ report }) {
  const score = report.overall_risk_score ?? 0;
  const display = riskDisplay(report.risk_level);
  const degrees = score * 3.6;
  const failedCount = report.failed_document_count ?? 0;
  const totalDocs = report.total_scored_documents ?? 4;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="grid grid-cols-1 items-center gap-8 lg:grid-cols-[auto_1fr]">
          <div className="flex flex-col items-center gap-3">
            <div
              className="relative flex h-36 w-36 items-center justify-center rounded-full"
              style={{
                background: `conic-gradient(${display.ringColor} 0deg ${degrees}deg, #e2e8f0 ${degrees}deg 360deg)`,
              }}
              role="img"
              aria-label={`Overall risk score ${score}`}
            >
              <div className="flex h-[7.25rem] w-[7.25rem] flex-col items-center justify-center rounded-full bg-white shadow-inner">
                <span className="text-3xl font-bold text-slate-900">{score}</span>
                <span className="text-xs text-slate-500">/ 100</span>
              </div>
            </div>
            <Badge variant="outline" className={display.className}>
              {display.label}
            </Badge>
          </div>

          <div className="space-y-6">
            <div>
              <p className="text-sm font-medium text-slate-700">
                Failed documents: {failedCount} / {totalDocs}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Each failed document contributes +25 to the overall risk score.
              </p>
            </div>
            <RiskScale score={score} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
