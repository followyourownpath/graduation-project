import { mockSubmissions, mockDocuments, mockExtractedData } from './mock-data';

// Set this to true to use real API endpoints once the backend is ready
const USE_REAL_API = true;
const BASE_URL = 'http://localhost:5000/api/v1'; // Adjust to your actual backend URL later

import { supabase } from './supabase';

const getAuthHeaders = async (existingHeaders = {}) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    return {
      ...existingHeaders,
      'Authorization': `Bearer ${session.access_token}`
    };
  }
  return existingHeaders;
};

// Delay helper to simulate network latency for mock data
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const api = {
  /**
   * Create a new application submission with uploaded files
   * @param {FormData} formData - Contains customer_name, loan_type, files[], document_types[]
   */
  async createSubmission(formData) {
    if (USE_REAL_API) {
      // Step 1: Create application
      const customer_name = formData.get('customer_name');
      const loan_type = formData.get('loan_type');
      
      const appRes = await fetch(`${BASE_URL}/applications`, {
        method: 'POST',
        headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ customer_name, loan_type, source_channel: 'frontend' })
      });
      
      if (!appRes.ok) {
        const err = await appRes.json().catch(() => ({}));
        throw new Error(err.error?.message || 'Failed to create application');
      }
      
      const appData = await appRes.json();
      const submissionId = appData.submission_id;

      // Step 2: Upload documents one by one
      const files = formData.getAll('files');
      const docTypes = formData.getAll('document_types');
      const docIds = [];
      
      for (let i = 0; i < files.length; i++) {
        const docFormData = new FormData();
        docFormData.append('file', files[i]);
        docFormData.append('document_type', docTypes[i]);
        
        const docRes = await fetch(`${BASE_URL}/submissions/${submissionId}/documents`, {
          method: 'POST',
          headers: await getAuthHeaders(),
          body: docFormData
        });
        
        if (!docRes.ok) {
           console.error(`Failed to upload ${files[i].name}`);
        } else {
           const docData = await docRes.json();
           docIds.push({ id: docData.id, name: files[i].name });
        }
      }
      
      // Step 3: Trigger OCR parsing sequentially in the background
      // This prevents Azure rate limiting (429) and backend thread pool exhaustion (503)
      (async () => {
        for (const doc of docIds) {
          try {
            const ocrRes = await fetch(`${BASE_URL}/documents/${doc.id}/ocr`, { 
              method: 'POST',
              headers: await getAuthHeaders()
            });
            if (!ocrRes.ok) console.error(`OCR failed for ${doc.name} with status ${ocrRes.status}`);
          } catch (err) {
            console.error(`OCR request error for ${doc.name}:`, err);
          }
        }
      })();
      
      return { submission_id: submissionId, message: 'Upload successful, OCR processing started' };
    } else {
      await delay(1500);
      // Simulate success and return a mock ID (using the first one to show data in review page)
      return {
        submission_id: 'sub-2026-001',
        message: 'Upload successful, OCR processing started'
      };
    }
  },

  /**
   * Get submission details and its documents
   * @param {string} id - Submission ID
   */
  async getSubmission(id) {
    if (USE_REAL_API) {
      const res = await fetch(`${BASE_URL}/submissions/${id}`, {
        headers: await getAuthHeaders()
      });
      if (!res.ok) throw new Error('Failed to fetch submission');
      return res.json();
    } else {
      await delay(800);
      const submission = mockSubmissions.find(s => s.id === id);
      if (!submission) throw new Error('Submission not found');
      
      return {
        ...submission,
        documents: mockDocuments[id] || []
      };
    }
  },

  /**
   * Get a list of submissions for the dashboard
   * @param {Object} params - Query parameters (page, limit, status, etc.)
   */
  async getSubmissions(params = {}) {
    if (USE_REAL_API) {
      const queryString = new URLSearchParams(params).toString();
      const res = await fetch(`${BASE_URL}/submissions?${queryString}`, {
        headers: await getAuthHeaders()
      });
      if (!res.ok) throw new Error('Failed to fetch submissions');
      return res.json();
    } else {
      await delay(800);
      return {
        total_count: mockSubmissions.length,
        data: mockSubmissions
      };
    }
  },

  /**
   * Get extracted OCR data for a specific document
   * @param {string} docId - Document ID
   */
  async getExtractedData(docId) {
    if (USE_REAL_API) {
      const res = await fetch(`${BASE_URL}/documents/${docId}/extracted-data`, {
        headers: await getAuthHeaders()
      });
      if (!res.ok) throw new Error('Failed to fetch extracted data');
      return res.json();
    } else {
      await delay(800);
      return mockExtractedData[docId] || { doc_id: docId, fields: [] };
    }
  },

  /**
   * Save human corrections to a specific field
   * @param {string} fieldId - Extracted field ID
   * @param {Object} data - { corrected_value, review_status, review_notes }
   */
  async saveFieldReview(fieldId, data) {
    if (USE_REAL_API) {
      const res = await fetch(`${BASE_URL}/fields/${fieldId}/review`, {
        method: 'PUT',
        headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error('Failed to save field review');
      return res.json();
    } else {
      await delay(500);
      // In mock mode, we just return success
      return { message: 'Updated successfully' };
    }
  },

  /**
   * Update the status of a submission (Approve/Reject)
   * @param {string} submissionId - Submission ID
   * @param {string} status - 'approved' or 'rejected'
   */
  async updateSubmissionStatus(submissionId, status) {
    if (USE_REAL_API) {
      const res = await fetch(`${BASE_URL}/submissions/${submissionId}/status`, {
        method: 'PUT',
        headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error('Failed to update submission status');
      return res.json();
    } else {
      await delay(500);
      return { message: 'Updated successfully' };
    }
  }
};
