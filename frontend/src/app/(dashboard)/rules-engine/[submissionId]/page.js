"use client";

import { useEffect, useMemo, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Loader2, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RiskScoreCard } from "@/components/rules-engine/risk-score-card";
import { DocumentResultRow } from "@/components/rules-engine/document-result-row";
import { RuleResultTable } from "@/components/rules-engine/rule-result-table";
import { api, ApiError } from "@/lib/api";
import { DOCUMENT_TYPE_ORDER } from "@/lib/risk-display";

export default function RiskAssessmentReportPage({ params }) {
  const unwrappedParams = use(params);
  const submissionId = unwrappedParams.submissionId;
  const router = useRouter();

  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  async function loadReport() {
    setLoading(true);
    setError("");
    setNotFound(false);
    try {
      const data = await api.getRiskAssessment(submissionId);
      setReport(data);
    } catch (err) {
      setReport(null);
      if (err instanceof ApiError && err.status === 404 && err.code === "risk_assessment_not_found") {
        setNotFound(true);
      } else {
        setError(err.message || "Failed to load risk assessment.");
        toast.error(err.message || "Failed to load risk assessment.");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleRetryLoad() {
    return loadReport();
  }

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await api.getRiskAssessment(submissionId);
        if (!active) return;
        setReport(data);
      } catch (err) {
        if (!active) return;
        setReport(null);
        if (err instanceof ApiError && err.status === 404 && err.code === "risk_assessment_not_found") {
          setNotFound(true);
        } else {
          setError(err.message || "Failed to load risk assessment.");
          toast.error(err.message || "Failed to load risk assessment.");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [submissionId]);

  const orderedDocuments = useMemo(() => {
    const byType = new Map((report?.document_results || []).map((doc) => [doc.document_type, doc]));
    return DOCUMENT_TYPE_ORDER.map((type) => byType.get(type)).filter(Boolean);
  }, [report]);

  async function handleStartAssessment() {
    if (starting) return;
    setStarting(true);
    try {
      const data = await api.startRiskAssessment(submissionId);
      setReport(data);
      setNotFound(false);
      setError("");
      toast.success("Risk assessment completed.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        toast.error(err.message);
      } else {
        toast.error(err.message || "Risk assessment failed.");
      }
    } finally {
      setStarting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8" aria-live="polite">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="sr-only">Loading risk assessment report</span>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="mx-auto max-w-2xl space-y-6 p-8 text-center">
        <h1 className="text-2xl font-bold text-slate-900">No risk assessment yet</h1>
        <p className="text-slate-500">
          This approved application has not been scored. Start an assessment to generate the Phase 1 report.
        </p>
        <div className="flex justify-center gap-3">
          <Button type="button" variant="outline" onClick={() => router.push("/rules-engine")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to list
          </Button>
          <Button
            type="button"
            className="bg-blue-600 hover:bg-blue-700"
            disabled={starting}
            onClick={handleStartAssessment}
          >
            {starting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Start Assessment
          </Button>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="mx-auto max-w-2xl space-y-6 p-8 text-center">
        <h1 className="text-2xl font-bold text-slate-900">Unable to load report</h1>
        <p className="text-slate-500">{error || "Something went wrong."}</p>
        <div className="flex justify-center gap-3">
          <Button type="button" variant="outline" onClick={() => router.push("/rules-engine")}>
            Back to list
          </Button>
          <Button type="button" onClick={handleRetryLoad}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link
            href="/rules-engine"
            className="mb-3 inline-flex items-center text-sm text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Rules Engine
          </Link>
          <h1 className="text-2xl font-bold text-slate-900">Risk Assessment Report</h1>
          <div className="mt-2 space-y-1 text-sm text-slate-600">
            <p>
              <span className="font-medium text-slate-500">Application Reference: </span>
              {report.application_reference || report.submission_id}
            </p>
            <p>
              <span className="font-medium text-slate-500">Applicant: </span>
              {report.customer_name || "—"}
            </p>
            <p>
              <span className="font-medium text-slate-500">Report Date: </span>
              {report.assessed_at ? new Date(report.assessed_at).toLocaleString() : "—"}
            </p>
          </div>
        </div>
        <Button type="button" variant="outline" disabled={starting} onClick={handleStartAssessment}>
          {starting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          Recalculate
        </Button>
      </div>

      <RiskScoreCard report={report} />

      <Card>
        <CardHeader>
          <CardTitle>Document Results</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <DocumentResultRow baseline />
          {orderedDocuments.map((doc) => (
            <DocumentResultRow key={doc.document_type} document={doc} />
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <RuleResultTable documentResults={report.document_results} />
        </CardContent>
      </Card>
    </div>
  );
}
