import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApplicationMobileCard } from "@/components/application-mobile-card";

describe("ApplicationMobileCard", () => {
  it("renders application status, risk, CRM link and review destination", () => {
    render(<ApplicationMobileCard showCrm app={{
      id: "submission-1",
      local_application_id: "APP-001",
      crm_application_id: "CRM-99",
      customer_name: "Alice Smith",
      loan_type: "purchase",
      submission_status: "in_review",
      assessment_status: "completed",
      overall_risk_score: 25,
      risk_level: "lower",
      created_at: "2026-08-05T10:30:00Z",
    }} />);

    expect(screen.getByRole("heading", { name: "Alice Smith" })).toBeVisible();
    expect(screen.getByText("in review")).toBeVisible();
    expect(screen.getByText(/25 · Lower Risk/)).toBeVisible();
    expect(screen.getByText("CRM-99")).toBeVisible();
    expect(screen.getByRole("link", { name: /review/i })).toHaveAttribute("href", "/application/submission-1");
  });

  it("uses safe fallbacks for incomplete records", () => {
    render(<ApplicationMobileCard app={{ id: "draft-1" }} />);
    expect(screen.getByRole("heading", { name: "Unnamed applicant" })).toBeVisible();
    expect(screen.getByText("draft")).toBeVisible();
    expect(screen.getByText("Not assessed")).toBeVisible();
  });
});
