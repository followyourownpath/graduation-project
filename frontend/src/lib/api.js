import { createClient } from "@/lib/supabase/client";

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export async function apiFetch(path, options = {}) {
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
};
