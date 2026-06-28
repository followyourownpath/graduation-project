# Frontend Design Document: AI Powered Mortgage Scoring Engine

## 1. Project Overview
The AI Powered Mortgage Scoring Engine is a platform designed to automate document verification, enhance compliance, and streamline the mortgage application review process. The primary users will be internal Compliance Officers and Administrators who need to review applications, verify extracted data, and assess fraud risks.

## 2. Target Audience & Roles
- **Compliance Officer / Analyst:** The main user who will review applications, resolve OCR discrepancies, check fraud alerts, and make compliance decisions.
- **Broker / Admin:** Users responsible for creating applications and uploading client documents.
*(Note: Complex RBAC is out of scope for the MVP, so role differentiation will be minimal initially).*

## 3. UI/UX Design Principles
- **Professional & Trustworthy:** Clean, modern, and data-centric design suitable for a financial enterprise application.
- **Scannability & Clarity:** Highlight critical risk indicators, mismatches, and fraud alerts using clear color coding (e.g., Red for high risk, Amber for warnings, Green for verified).
- **Efficiency:** The layout should minimize clicks for compliance officers by presenting side-by-side comparisons (e.g., original document viewer next to extracted data).
- **Responsive:** While primarily a desktop web application, it should gracefully handle different screen sizes.

## 4. Core Pages & User Journey (MVP Scope)

### 4.1. Authentication (Login Page)
- **Features:** Simple static login page for the MVP.
- **Design:** Clean branding, username/password fields, and an error state for invalid credentials.

### 4.2. Dashboard (Compliance Review Hub)
- **Features:** 
  - Overview of all active mortgage applications.
  - Quick metrics: Total applications, Pending reviews, High-risk applications.
  - Data table listing applications with columns for: Applicant Name, Loan Type, Date Submitted, Status, and **Overall Risk Score**.
  - Filtering and sorting (by Risk Category, Status, Loan Type).

### 4.3. Application Creation & Document Upload
- **Features:**
  - Form to create a new mortgage application.
  - Selection of "Loan Type" (which dictates the required document checklist).
  - Bulk document upload interface (Drag & Drop support for PDF, JPG, PNG).
  - Real-time upload status and file validation (size, type).

### 4.4. Application Detail & Review Page (The Core Interface)
This is the most critical page where officers spend their time.
- **Header Section:** Applicant summary (Name, DOB, Loan Type) and the Overall Application Risk Score.
- **Document Checklist Panel:** Status of required documents (Uploaded, Missing, Rejected).
- **OCR & Extraction Viewer (Split Screen / Side-by-Side):**
  - *Left Pane:* Document Viewer (PDF/Image renderer) to view the uploaded file (e.g., Payslip).
  - *Right Pane:* Extracted Data Form (Structured JSON data presented as editable form fields). Allows the officer to verify and correct low-confidence extractions.
- **Cross-Document Consistency & Fraud Alerts Panel:**
  - Highlights mismatches (e.g., "Payslip income does not match Bank Statement deposits").
  - Displays fraud indicators (e.g., "Suspicious metadata detected on ID document").
  - Rule-based compliance flags.
- **Action Bar:** Buttons to "Approve", "Flag for Review", or "Reject" the application, along with a notes/audit log section.

## 5. Technology Stack Recommendations
- **Framework:** React.js (Next.js or Vite for fast scaffolding) or Vue.js.
- **Styling:** Tailwind CSS for rapid, consistent styling, or a component library like MUI / Ant Design for enterprise-ready data tables and forms.
- **Document Viewing:** react-pdf or similar library to render PDFs natively in the browser.
- **State Management:** Zustand, Redux, or React Context (depending on complexity).
- **API Communication:** Axios or Fetch API to communicate with the Python/.NET/Node.js backend.

## 6. Future Considerations (Post-MVP)
- Integration with Smartfinn (auto-fill capability) and Mercury CRM.
- Advanced reporting and export capabilities.
- Complex Role-Based Access Control (RBAC).
