import { createClient } from "@/lib/supabase/client";
import { mockDocuments, mockExtractedData, mockSubmissions } from "@/lib/mock-data";

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status, code, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export async function apiFetch(path, options = {}) {
  if (process.env.NODE_ENV === "development" && process.env.NEXT_PUBLIC_UI_REVIEW_MODE === "1") {
    const idMatch = path.match(/^\/submissions\/([^/]+)$/);
    const documentMatch = path.match(/^\/documents\/([^/]+)\/extracted-data$/);
    if (path === "/auth/me") return { staff_profile: { full_name: "Jordan Lee", role: "reviewer" } };
    if (path.startsWith("/submissions?") || path === "/submissions") return { data: mockSubmissions };
    if (idMatch) {
      const submission = mockSubmissions.find((item) => item.id === idMatch[1]) || mockSubmissions[0];
      return { ...submission, documents: (mockDocuments[submission.id] || mockDocuments["sub-2026-001"]).map((document) => ({ ...document, storage_uri: null })) };
    }
    if (documentMatch) return mockExtractedData[documentMatch[1]] || { document_type: "document", fields: [] };
    if (path.includes("risk-assessment")) return { submission_id: "sub-2026-002", application_reference: "APP-2026-00902", customer_name: "Bob Johnson", assessed_at: "2026-08-05T06:30:00Z", overall_risk_score: 25, risk_level: "lower", failed_document_count: 1, total_scored_documents: 4, document_results: [{ document_type: "id_100", display_name: "Identity document", status: "pass", rules: [] }, { document_type: "payslip", display_name: "Payslip", status: "fail", rules: [{ rule_id: "PAY-001", label: "Employer name matches", status: "fail", document_field_keys: ["employer_name"], fact_find_field_keys: ["employment.employer"], fact_find_value: "Acme Finance Pty Ltd", document_value: "Acme Financial Services", message: "Employer names differ." }] }, { document_type: "bank_statement_3m", display_name: "Bank statement", status: "pass", rules: [] }, { document_type: "ato_notice", display_name: "ATO notice", status: "pass", rules: [] }] };
  }
  const supabase = createClient();
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error || !session?.access_token) {
    throw new ApiError("Your session has expired. Please sign in again.", 401, "session_required");
  }

  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${session.access_token}`);
  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const apiError = new ApiError(
      body.error?.message || `Request failed with status ${response.status}.`,
      response.status,
      body.error?.code,
      body.error?.details ?? null,
    );
    if (response.status === 401) await supabase.auth.signOut();
    throw apiError;
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  getCurrentStaff: () => apiFetch("/auth/me"),

  async createSubmission(formData) {
    const application = await apiFetch("/applications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: formData.get("customer_name"),
        loan_type: formData.get("loan_type"),
        source_channel: "frontend",
      }),
    });
    const files = formData.getAll("files");
    const documentTypes = formData.getAll("document_types");
    const documents = [];
    for (let index = 0; index < files.length; index += 1) {
      const upload = new FormData();
      upload.append("file", files[index]);
      upload.append("document_type", documentTypes[index]);
      documents.push(await apiFetch(`/submissions/${application.submission_id}/documents`, {
        method: "POST",
        body: upload,
      }));
    }
    void (async () => {
      for (const document of documents) {
        try {
          await apiFetch(`/documents/${document.id}/ocr`, { method: "POST" });
        } catch (error) {
          console.error(`OCR request failed for document ${document.id}:`, error);
        }
      }
    })();
    return { submission_id: application.submission_id, message: "Upload and OCR started successfully" };
  },

  getSubmission: (id) => apiFetch(`/submissions/${encodeURIComponent(id)}`),
  getSubmissions(params = {}) {
    const query = new URLSearchParams(params).toString();
    return apiFetch(`/submissions${query ? `?${query}` : ""}`);
  },
  getExtractedData: (id) => apiFetch(`/documents/${encodeURIComponent(id)}/extracted-data`),
  saveFieldReview(id, data) {
    return apiFetch(`/fields/${encodeURIComponent(id)}/review`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },
  updateSubmissionStatus(id, status) {
    return apiFetch(`/submissions/${encodeURIComponent(id)}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
  },
  getApprovedSubmissions() {
    return apiFetch("/submissions?status=approved");
  },

  startRiskAssessment(submissionId) {
    return apiFetch(`/submissions/${encodeURIComponent(submissionId)}/risk-assessment`, {
      method: "POST",
    });
  },

  getRiskAssessment(submissionId) {
    return apiFetch(`/submissions/${encodeURIComponent(submissionId)}/risk-assessment`);
  },

  retryCrmSync(id) {
    return apiFetch(`/submissions/${encodeURIComponent(id)}/sync/retry`, {
      method: "POST",
    });
  },
};
