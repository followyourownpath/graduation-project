import Link from "next/link";
import { ArrowRight, Building2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/formatters";
import { formatRiskScoreBadge, loanTypeLabel, riskDisplay } from "@/lib/risk-display";

function submissionClass(status) {
  return status === "approved" ? "border-emerald-300 bg-emerald-50 text-emerald-700" : status === "rejected" ? "border-red-300 bg-red-50 text-red-700" : status === "in_review" ? "border-amber-300 bg-amber-50 text-amber-700" : "border-slate-300 bg-slate-100 text-slate-700";
}

export function ApplicationMobileCard({ app, showCrm = false }) {
  const riskBadge = formatRiskScoreBadge(app);
  const risk = riskDisplay(app.risk_level);
  return <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><h2 className="truncate font-semibold text-slate-950">{app.customer_name || "Unnamed applicant"}</h2><p className="mt-1 font-mono text-xs text-slate-500">{app.local_application_id || app.id}</p></div><Badge variant="outline" className={submissionClass(app.submission_status)}>{String(app.submission_status || "draft").replace("_", " ")}</Badge></div><div className="mt-4 grid grid-cols-2 gap-3 border-y border-slate-100 py-3 text-xs"><div><p className="text-slate-500">Loan type</p><p className="mt-1 font-medium text-slate-700">{loanTypeLabel(app.loan_type)}</p></div><div><p className="text-slate-500">Submitted</p><p className="mt-1 font-medium text-slate-700">{formatDate(app.created_at)}</p></div></div><div className="mt-3 flex items-center justify-between gap-2"><div className="flex min-w-0 items-center gap-2"><Badge variant="outline" className={riskBadge.className}>{riskBadge.scoreText != null ? `${riskBadge.scoreText} · ${risk.label}` : riskBadge.label}</Badge>{showCrm && <span className="flex items-center gap-1 truncate text-xs text-slate-500"><Building2 className="h-3.5 w-3.5" />{app.crm_application_id || "Not linked"}</span>}</div><Link href={`/application/${app.id}`} className="shrink-0"><Button variant="ghost" size="sm">Review <ArrowRight className="ml-1 h-3.5 w-3.5" /></Button></Link></div></article>;
}
