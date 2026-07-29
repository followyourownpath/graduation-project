# Frontend Page Interaction and Logic

This document describes page navigation, state management, and component choices for the
mortgage compliance scoring system based on the business requirements and visual designs.

## 1. Technical Standards and UI Components

- **Framework:** Next.js App Router
- **Styling:** Tailwind CSS
- **UI primitives:** Accessible, unstyled Radix UI Primitives
- **Component layer:** [shadcn/ui](https://ui.shadcn.com/) components built on Radix UI, such as
  Dialog, Select, Accordion, and Tabs
- **Icons:** Lucide React
- **State management:** Zustand or React Context

## 2. Core Routes

- `/login`: Sign-in page for static validation or JWT retrieval
- `/dashboard`: Review dashboard with summary data and urgent work
- `/applications`: Complete application list and application-creation entry point
- `/applications/new`: New mortgage application with multi-file drag-and-drop upload
- `/application/[id]`: Application details and review workspace

---

## 3. Page Logic and Component Structure

### 3.1 Login (`/login`)

- **Layout:**
  - Left: Brand, product statement, and geometric background.
  - Right: Login form card.
- **Components:** `Form`, `Label`, `Checkbox` for Remember Me, and `Button`.
- **Interactions:**
  1. Validate that the email and password are present and that the email format is valid.
  2. Submit the login request and show a loading state on the button.
  3. On success, store the JWT in an HTTP-only cookie or local storage and navigate to
     `/dashboard`.
  4. On failure, display a toast notification.

### 3.2 Dashboard (`/dashboard`)

- **Layout:**
  - Header and sidebar navigation.
  - Summary statistic cards.
  - A table of recent urgent applications.
- **Components:** `NavigationMenu`, `DropdownMenu`, and `Card`.
- **Interaction:** Present system health and prioritise high-risk or pending cases that require
  human review.

### 3.3 Applications (`/applications`)

- **Layout:**
  - Header with a prominent `+ New Application` button.
  - Data table and filters.
- **Components:** `Select`, `Table`, and `Badge`.
- **Interactions:**
  1. Filter by status, risk level, and loan type, then reload the data.
  2. Colour risk scores red for high, amber for medium, and green for low.
  3. Navigate to `/applications/new` from `+ New Application`.
  4. Navigate to `/application/[id]` from a row's Review action.

### 3.4 New Application (`/applications/new`)

- **Layout:**
  - Applicant information form.
  - Large dashed drag-and-drop upload target.
  - Selected-file queue with progress indicators.
  - Submit button.
- **Interactions:**
  1. Highlight the drop target while files are dragged over it.
  2. Add selected files to the queue and update progress dynamically. Use blue while uploading
     and a green check when complete.
  3. Enable Submit Application only after every file reaches `completed`, then return to
     `/applications`.

### 3.5 Application Review (`/application/[id]`)

- **Layout:**
  - Header with applicant summary, dashboard navigation, and application status.
  - Left pane with the original PDF or image.
  - Right pane with extracted OCR fields and cross-document alerts.
- **Components:** `ScrollArea`, `Tabs`, `Accordion`, `Dialog`, and `Popover`.
- **Interactions:**
  1. Load the source file URL, structured OCR result, and risk alerts concurrently.
  2. Keep the form and alerts in sync when the reviewer changes the selected document.
  3. Allow reviewers to override incorrect extracted values and mark changed fields as `Edited`.
  4. Display cross-document discrepancies prominently and support Mark Resolved and Add Note.
  5. Require confirmation and a reason before submitting an Approve or Reject decision.

## 4. API Errors and Long-Running Operations

- Show progress and use long polling or WebSocket updates for file upload and OCR operations.
- Catch failures such as OCR errors and corrupt files, and present them consistently through
  toast notifications.
