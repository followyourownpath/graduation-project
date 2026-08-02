"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Filter, Loader2, RefreshCw, Search, ShieldAlert } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import {
  assessmentStatusDisplay,
  formatRiskScoreBadge,
  loanTypeLabel,
  riskDisplay,
} from "@/lib/risk-display";

function formatReadinessDetails(details) {
  if (details == null) return [];
  if (Array.isArray(details)) {
    return details.map((item) => (typeof item === "string" ? item : JSON.stringify(item)));
  }
  if (typeof details === "string") return [details];
  if (typeof details === "object") {
    return Object.entries(details).flatMap(([key, value]) => {
      if (Array.isArray(value)) return value.map((item) => `${key}: ${item}`);
      return [`${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`];
    });
  }
  return [String(details)];
}

export default function RulesEnginePage() {
  const router = useRouter();
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [processingIds, setProcessingIds] = useState(() => new Set());
  const [readinessDialog, setReadinessDialog] = useState({ open: false, message: "", details: [] });

  async function loadSubmissions() {
    setLoading(true);
    setLoadError("");
    try {
      const response = await api.getApprovedSubmissions();
      const rows = (response.data || []).filter(
        (row) => row.submission_status === "approved" || !row.submission_status,
      );
      setSubmissions(rows);
    } catch (error) {
      setLoadError(error.message || "Failed to load approved applications.");
      toast.error(error.message || "Failed to load approved applications.");
    } finally {
      setLoading(false);
    }
  }

  function handleRefresh() {
    return loadSubmissions();
  }

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const response = await api.getApprovedSubmissions();
        if (!active) return;
        const rows = (response.data || []).filter(
          (row) => row.submission_status === "approved" || !row.submission_status,
        );
        setSubmissions(rows);
      } catch (error) {
        if (!active) return;
        setLoadError(error.message || "Failed to load approved applications.");
        toast.error(error.message || "Failed to load approved applications.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return submissions.filter((row) => {
      const appId = String(row.local_application_id || row.id || "").toLowerCase();
      const crmId = String(row.crm_application_id || "").toLowerCase();
      const name = String(row.customer_name || "").toLowerCase();
      const matchesSearch = !query
        || appId.includes(query)
        || crmId.includes(query)
        || name.includes(query);

      const assessmentStatus = row.assessment_status || "not_started";
      const matchesStatus = statusFilter === "all" || assessmentStatus === statusFilter;

      const matchesRisk = riskFilter === "all"
        || (riskFilter === "not_assessed" && !row.risk_level)
        || row.risk_level === riskFilter;

      return matchesSearch && matchesStatus && matchesRisk;
    });
  }, [submissions, searchQuery, statusFilter, riskFilter]);

  async function handleStartAssessment(submissionId) {
    if (processingIds.has(submissionId)) return;

    setProcessingIds((prev) => new Set(prev).add(submissionId));
    setSubmissions((prev) => prev.map((row) => (
      row.id === submissionId
        ? { ...row, assessment_status: "processing" }
        : row
    )));

    try {
      await api.startRiskAssessment(submissionId);
      router.push(`/rules-engine/${submissionId}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        const details = formatReadinessDetails(error.details);
        toast.error(error.message);
        setReadinessDialog({ open: true, message: error.message, details });
      } else {
        toast.error(error.message || "Risk assessment failed.");
      }
      await loadSubmissions();
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(submissionId);
        return next;
      });
    }
  }

  function renderActions(row) {
    const id = row.id;
    const status = processingIds.has(id) ? "processing" : (row.assessment_status || "not_started");

    if (status === "processing") {
      return (
        <Button size="sm" disabled>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Assessing…
        </Button>
      );
    }

    if (status === "completed") {
      return (
        <div className="flex flex-wrap gap-2">
          <Link href={`/rules-engine/${id}`}>
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700">View Report</Button>
          </Link>
          <Button size="sm" variant="outline" onClick={() => handleStartAssessment(id)}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Recalculate
          </Button>
        </div>
      );
    }

    if (status === "failed") {
      return (
        <Button size="sm" variant="outline" onClick={() => handleStartAssessment(id)}>
          Retry Assessment
        </Button>
      );
    }

    return (
      <Button size="sm" className="bg-blue-600 hover:bg-blue-700" onClick={() => handleStartAssessment(id)}>
        Start Assessment
      </Button>
    );
  }

  return (
    <div className="space-y-6 p-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
            <ShieldAlert className="h-6 w-6 text-blue-600" />
            Rules Engine
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Run Phase 1 Fact Find comparisons on approved applications.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={handleRefresh} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader className="border-b border-slate-100 pb-3">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <div className="relative w-full sm:w-96">
              <Search className="absolute top-2.5 left-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search by Applicant or Application ID..."
                className="pl-9"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />
            </div>
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-[180px]">
                  <Filter className="mr-2 h-4 w-4 text-slate-500" />
                  <SelectValue placeholder="Assessment Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="not_started">Not started</SelectItem>
                  <SelectItem value="processing">Assessing</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
              <Select value={riskFilter} onValueChange={setRiskFilter}>
                <SelectTrigger className="w-full sm:w-[180px]">
                  <Filter className="mr-2 h-4 w-4 text-slate-500" />
                  <SelectValue placeholder="Risk Level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All risk levels</SelectItem>
                  <SelectItem value="not_assessed">Not assessed</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="lower">Lower</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="higher">Higher</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {loading ? (
            <div className="flex justify-center p-12" aria-live="polite">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
              <span className="sr-only">Loading approved applications</span>
            </div>
          ) : loadError ? (
            <div className="space-y-4 py-10 text-center">
              <p className="text-slate-600">{loadError}</p>
              <Button type="button" onClick={handleRefresh}>Retry</Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Application</TableHead>
                    <TableHead>Applicant</TableHead>
                    <TableHead>Loan Type</TableHead>
                    <TableHead>Application Date</TableHead>
                    <TableHead>Assessment Status</TableHead>
                    <TableHead>Risk Score</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((row) => {
                    const assessmentStatus = processingIds.has(row.id)
                      ? "processing"
                      : (row.assessment_status || "not_started");
                    const statusDisplay = assessmentStatusDisplay(assessmentStatus);
                    const riskBadge = formatRiskScoreBadge({
                      assessment_status: assessmentStatus,
                      overall_risk_score: row.overall_risk_score,
                      risk_level: row.risk_level,
                    });
                    const risk = riskDisplay(row.risk_level);

                    return (
                      <TableRow key={row.id}>
                        <TableCell className="font-medium">
                          <div className="flex flex-col gap-1">
                            <span className="font-mono text-xs font-semibold text-slate-900">
                              {row.local_application_id || row.id}
                            </span>
                            {row.crm_application_id ? (
                              <span className="text-[11px] text-slate-500">CRM: {row.crm_application_id}</span>
                            ) : null}
                          </div>
                        </TableCell>
                        <TableCell>{row.customer_name}</TableCell>
                        <TableCell>{loanTypeLabel(row.loan_type)}</TableCell>
                        <TableCell>{row.created_at ? new Date(row.created_at).toLocaleDateString() : "—"}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={statusDisplay.className}>
                            {statusDisplay.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={riskBadge.className}>
                            {riskBadge.scoreText != null
                              ? `${riskBadge.scoreText} (${risk.label})`
                              : riskBadge.label}
                          </Badge>
                        </TableCell>
                        <TableCell>{renderActions(row)}</TableCell>
                      </TableRow>
                    );
                  })}
                  {filtered.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="py-8 text-center text-slate-500">
                        No approved applications match your filters.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={readinessDialog.open}
        onOpenChange={(open) => setReadinessDialog((prev) => ({ ...prev, open }))}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assessment not ready</DialogTitle>
            <DialogDescription>{readinessDialog.message}</DialogDescription>
          </DialogHeader>
          {readinessDialog.details.length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
              {readinessDialog.details.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
