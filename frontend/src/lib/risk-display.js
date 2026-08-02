export const RISK_DISPLAY = {
  low: {
    label: "Low Risk",
    score: 0,
    className: "border-emerald-500 text-emerald-700 bg-emerald-50",
    ringColor: "#10b981",
  },
  lower: {
    label: "Lower Risk",
    score: 25,
    className: "border-sky-500 text-sky-700 bg-sky-50",
    ringColor: "#0ea5e9",
  },
  medium: {
    label: "Medium Risk",
    score: 50,
    className: "border-amber-500 text-amber-700 bg-amber-50",
    ringColor: "#f59e0b",
  },
  higher: {
    label: "Higher Risk",
    score: 75,
    className: "border-orange-500 text-orange-700 bg-orange-50",
    ringColor: "#f97316",
  },
  high: {
    label: "High Risk",
    score: 100,
    className: "border-red-500 text-red-700 bg-red-50",
    ringColor: "#ef4444",
  },
};

const NOT_ASSESSED = {
  label: "Not assessed",
  score: null,
  className: "border-slate-300 text-slate-600 bg-slate-100",
  ringColor: "#94a3b8",
};

const ASSESSMENT_STATUS_DISPLAY = {
  not_started: { label: "Not started", className: "border-slate-300 text-slate-600 bg-slate-100" },
  processing: { label: "Assessing…", className: "border-blue-400 text-blue-700 bg-blue-50" },
  completed: { label: "Completed", className: "border-emerald-500 text-emerald-700 bg-emerald-50" },
  failed: { label: "Assessment failed", className: "border-red-500 text-red-700 bg-red-50" },
};

const DOCUMENT_STATUS_DISPLAY = {
  pass: { label: "Pass", className: "border-emerald-500 text-emerald-700 bg-emerald-50" },
  fail: { label: "Fail", className: "border-red-500 text-red-700 bg-red-50" },
  not_applicable: { label: "N/A", className: "border-slate-300 text-slate-600 bg-slate-100" },
  incomplete: { label: "Incomplete", className: "border-amber-500 text-amber-700 bg-amber-50" },
  error: { label: "Error", className: "border-red-500 text-red-700 bg-red-50" },
};

export function riskDisplay(level) {
  if (level == null || level === "") return NOT_ASSESSED;
  return RISK_DISPLAY[level] ?? NOT_ASSESSED;
}

export function formatRiskScoreBadge({ assessment_status, overall_risk_score, risk_level } = {}) {
  if (assessment_status === "failed") {
    return {
      label: "Assessment failed",
      scoreText: null,
      className: ASSESSMENT_STATUS_DISPLAY.failed.className,
    };
  }

  if (assessment_status !== "completed") {
    return {
      label: "Not assessed",
      scoreText: null,
      className: NOT_ASSESSED.className,
    };
  }

  const display = riskDisplay(risk_level);
  const score = overall_risk_score ?? null;
  return {
    label: display.label,
    scoreText: score === null ? null : String(score),
    className: display.className,
  };
}

export function assessmentStatusDisplay(status) {
  if (status == null || status === "") {
    return ASSESSMENT_STATUS_DISPLAY.not_started;
  }
  return ASSESSMENT_STATUS_DISPLAY[status] ?? {
    label: String(status),
    className: NOT_ASSESSED.className,
  };
}

export function documentStatusDisplay(status) {
  if (status == null || status === "") {
    return { label: "Unknown", className: NOT_ASSESSED.className };
  }
  if (status === "N/A" || status === "n/a") {
    return DOCUMENT_STATUS_DISPLAY.not_applicable;
  }
  return DOCUMENT_STATUS_DISPLAY[status] ?? {
    label: String(status),
    className: NOT_ASSESSED.className,
  };
}

/**
 * Mask account numbers for display: show only last 4 digits as •••• 1234.
 * Leaves already-short/null values safe; does not log full values.
 */
export function maskAccountNumber(value) {
  if (value == null || value === "") return value;
  const digits = String(value).replace(/\D/g, "");
  if (digits.length === 0) return "••••";
  const last4 = digits.slice(-4);
  return `•••• ${last4}`;
}

export function formatMatchedApplicants(numbers) {
  if (!Array.isArray(numbers) || numbers.length === 0) return null;
  if (numbers.length === 1) return `Matched to Applicant ${numbers[0]}`;
  return `Matched to Applicants ${numbers.join(" & ")}`;
}

export const DOCUMENT_TYPE_ORDER = ["id_100", "payslip", "bank_statement_3m", "ato_notice"];

export const LOAN_TYPE_LABELS = {
  purchase: "Owner-Occupier Purchase",
  investment: "Investment Purchase",
  refinance: "Refinance",
  first_home: "First Home Buyer",
  self_employed: "Self-Employed (any)",
};

export function loanTypeLabel(loanType) {
  return LOAN_TYPE_LABELS[loanType] || loanType || "—";
}

/** Fields that should be masked when shown in the report UI. */
export function maybeMaskFieldValue(fieldKeys, value) {
  const keys = Array.isArray(fieldKeys) ? fieldKeys : [];
  const isAccount = keys.some((key) =>
    String(key).toLowerCase().includes("account_number")
  );
  if (isAccount) return maskAccountNumber(value);
  return value;
}
