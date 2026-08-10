import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DocumentResultRow } from "@/components/rules-engine/document-result-row";

const document = {
  display_name: "Bank statement",
  original_file_name: "statement.pdf",
  status: "fail",
  score: 25,
  matched_applicant_numbers: [1],
  rules: [{
    rule_id: "BANK-001",
    label: "Account number matches",
    status: "fail",
    message: "Account numbers differ.",
    fact_find_field_keys: ["bank.account_number"],
    document_field_keys: ["account_number"],
    fact_find_value: "12345678",
    document_value: "87654321",
  }],
};

describe("DocumentResultRow", () => {
  it("expands and collapses rule evidence while masking account numbers", async () => {
    render(<DocumentResultRow document={document} />);
    const toggle = screen.getByRole("button", { name: /rules/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Account numbers differ.")).not.toBeInTheDocument();

    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Account numbers differ.")).toBeVisible();
    expect(screen.queryByText("12345678")).not.toBeInTheDocument();
    expect(screen.getAllByText(/••••/)).toHaveLength(2);

    await userEvent.click(toggle);
    expect(screen.queryByText("Account numbers differ.")).not.toBeInTheDocument();
  });

  it("renders Fact Find as an unscored baseline without an expand button", () => {
    render(<DocumentResultRow document={{}} baseline />);
    expect(screen.getByText("Fact Find")).toBeVisible();
    expect(screen.getByText("Baseline")).toBeVisible();
    expect(screen.queryByRole("button", { name: /rules/i })).not.toBeInTheDocument();
  });
});
