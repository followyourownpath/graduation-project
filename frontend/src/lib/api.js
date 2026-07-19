import { mockSubmissions, mockDocuments, mockExtractedData } from './mock-data';

// Set this to true to use real API endpoints once the backend is ready
const USE_REAL_API = false;
const BASE_URL = '/api'; // Adjust to your actual backend URL later

// Delay helper to simulate network latency for mock data
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const api = {
  /**
   * Create a new application submission with uploaded files
   * @param {FormData} formData - Contains customer_name, loan_type, files[], document_types[]
   */
  async createSubmission(formData) {
    if (USE_REAL_API) {
      const res = await fetch(`${BASE_URL}/submissions`, {
        method: 'POST',
        body: formData, // No Content-Type header needed for FormData
      });
      if (!res.ok) throw new Error('Failed to create submission');
      return res.json();
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
      const res = await fetch(`${BASE_URL}/submissions/${id}`);
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
      const res = await fetch(`${BASE_URL}/submissions?${queryString}`);
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
      const res = await fetch(`${BASE_URL}/documents/${docId}/extracted-data`);
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error('Failed to save field review');
      return res.json();
    } else {
      await delay(500);
      // In mock mode, we just return success
      return { message: 'Updated successfully' };
    }
  }
};
