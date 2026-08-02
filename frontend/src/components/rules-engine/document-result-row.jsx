"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight, FileText } from "lucide-react";
import {
  documentStatusDisplay,
  formatMatchedApplicants,
  maybeMaskFieldValue,
} from "@/lib/risk-display";
import { cn } from "@/lib/utils";

function RuleMiniList({ rules }) {
  if (!rules?.length) {
    return <p className="text-sm text-slate-500">No rules returned for this document.</p>;
  }

  return (
    <ul className="space-y-2">
      {rules.map((rule) => {
        const status = documentStatusDisplay(rule.status);
        return (
          <li
            key={rule.rule_id}
            className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium text-slate-800">
                <span className="font-mono text-xs text-slate-500">{rule.rule_id}</span>
                {" — "}
                {rule.label}
              </span>
              <Badge variant="outline" className={status.className}>{status.label}</Badge>
            </div>
            {rule.message && <p className="mt-1 text-xs text-slate-500">{rule.message}</p>}
            {(rule.fact_find_value != null || rule.document_value != null) && (
              <div className="mt-2 grid gap-1 text-xs text-slate-600 sm:grid-cols-2">
                <p>
                  <span className="font-medium text-slate-500">Fact Find: </span>
                  {String(maybeMaskFieldValue(rule.fact_find_field_keys, rule.fact_find_value) ?? "—")}
                </p>
                <p>
                  <span className="font-medium text-slate-500">Document: </span>
                  {String(maybeMaskFieldValue(rule.document_field_keys, rule.document_value) ?? "—")}
                </p>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function DocumentResultRow({ document, baseline = false }) {
  const [expanded, setExpanded] = useState(false);
  const status = baseline
    ? { label: "Baseline", className: "border-indigo-400 text-indigo-700 bg-indigo-50" }
    : documentStatusDisplay(document?.status);
  const matched = formatMatchedApplicants(document?.matched_applicant_numbers);
  const scoreLabel = baseline ? "—" : document?.score ? `+${document.score}` : "0";

  return (
    <div className={cn("rounded-lg border border-slate-200 bg-white", baseline && "bg-slate-50")}>
      <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-500">
            <FileText className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-semibold text-slate-900">
                {baseline ? "Fact Find" : document?.display_name}
              </h4>
              <Badge variant="outline" className={status.className}>{status.label}</Badge>
            </div>
            <p className="mt-1 truncate text-sm text-slate-500">
              {baseline
                ? "Comparison baseline — not scored"
                : document?.original_file_name || "—"}
            </p>
            {matched && <p className="mt-1 text-xs font-medium text-slate-600">{matched}</p>}
          </div>
        </div>

        <div className="flex items-center gap-3 self-end sm:self-auto">
          <span
            className={cn(
              "text-sm font-semibold tabular-nums",
              !baseline && document?.score > 0 ? "text-red-600" : "text-slate-500",
            )}
          >
            {scoreLabel}
          </span>
          {!baseline && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-expanded={expanded}
              onClick={() => setExpanded((value) => !value)}
            >
              {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              Rules
            </Button>
          )}
        </div>
      </div>

      {!baseline && expanded && (
        <div className="border-t border-slate-100 bg-slate-50/80 px-4 py-3">
          <RuleMiniList rules={document?.rules} />
        </div>
      )}
    </div>
  );
}
