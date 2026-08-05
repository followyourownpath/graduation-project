"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  documentStatusDisplay,
  maybeMaskFieldValue,
} from "@/lib/risk-display";

function flattenRules(documentResults, { failsOnly }) {
  const rows = [];
  for (const doc of documentResults || []) {
    for (const rule of doc.rules || []) {
      if (failsOnly && rule.status !== "fail") continue;
      rows.push({
        ...rule,
        document_display_name: doc.display_name,
        document_type: doc.document_type,
      });
    }
  }
  return rows;
}

function ComparisonDetails({ rule }) {
  const comparison = rule.comparison;
  if (!comparison && rule.normalised_fact_find_value == null && rule.normalised_document_value == null) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
      {(rule.normalised_fact_find_value != null || rule.normalised_document_value != null) && (
        <p>
          Normalised:{" "}
          <span className="font-medium">
            {String(maybeMaskFieldValue(rule.fact_find_field_keys, rule.normalised_fact_find_value) ?? "—")}
          </span>
          {" vs "}
          <span className="font-medium">
            {String(maybeMaskFieldValue(rule.document_field_keys, rule.normalised_document_value) ?? "—")}
          </span>
        </p>
      )}
      {comparison && (
        <p>
          {comparison.operator && <span className="mr-2">Operator: {comparison.operator}</span>}
          {comparison.similarity != null && (
            <span className="mr-2">Similarity: {comparison.similarity}</span>
          )}
          {comparison.difference != null && (
            <span className="mr-2">Difference: {comparison.difference}</span>
          )}
          {comparison.threshold != null && <span>Threshold: {comparison.threshold}</span>}
        </p>
      )}
      {rule.message && <p>{rule.message}</p>}
    </div>
  );
}

export function RuleResultTable({ documentResults }) {
  const [showAll, setShowAll] = useState(false);
  const [expandedIds, setExpandedIds] = useState(() => new Set());

  const rows = useMemo(
    () => flattenRules(documentResults, { failsOnly: !showAll }),
    [documentResults, showAll],
  );

  function toggleRow(ruleId) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(ruleId)) next.delete(ruleId);
      else next.add(ruleId);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Field Mismatch Details</h3>
          <p className="text-sm text-slate-500">
            {showAll ? "Showing all rule results." : "Showing failed rules only."}
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => setShowAll((value) => !value)}>
          {showAll ? "Show failed only" : "Show all rules"}
        </Button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Document</TableHead>
              <TableHead>Rule</TableHead>
              <TableHead>Compared Field</TableHead>
              <TableHead>Fact Find Baseline</TableHead>
              <TableHead>Extracted Document Value</TableHead>
              <TableHead>Result</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((rule) => {
              const status = documentStatusDisplay(rule.status);
              const expanded = expandedIds.has(rule.rule_id + rule.document_type);
              const rowKey = `${rule.document_type}-${rule.rule_id}`;
              return (
                <TableRow key={rowKey} className="align-top">
                  <TableCell className="font-medium whitespace-normal">{rule.document_display_name}</TableCell>
                  <TableCell className="whitespace-normal">
                    <button
                      type="button"
                      className="text-left hover:underline"
                      aria-expanded={expanded}
                      onClick={() => toggleRow(rule.rule_id + rule.document_type)}
                    >
                      <span className="block font-mono text-xs text-slate-500">{rule.rule_id}</span>
                      <span className="text-sm text-slate-800">{rule.label}</span>
                    </button>
                    {expanded && <ComparisonDetails rule={rule} />}
                  </TableCell>
                  <TableCell className="max-w-[180px] text-sm text-slate-600 whitespace-normal">
                    {(rule.document_field_keys || []).join(", ") || "—"}
                  </TableCell>
                  <TableCell className="max-w-[200px] break-words text-sm whitespace-normal">
                    {String(maybeMaskFieldValue(rule.fact_find_field_keys, rule.fact_find_value) ?? "—")}
                  </TableCell>
                  <TableCell className="max-w-[200px] break-words text-sm whitespace-normal">
                    {String(maybeMaskFieldValue(rule.document_field_keys, rule.document_value) ?? "—")}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={status.className}>{status.label}</Badge>
                  </TableCell>
                </TableRow>
              );
            })}
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-slate-500">
                  {showAll ? "No rule results available." : "No failed rules — all comparisons passed or were not applicable."}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
