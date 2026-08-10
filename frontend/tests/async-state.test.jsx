import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EmptyState, InlineErrorState, PageLoadingState } from "@/components/async-state";

describe("async states", () => {
  it("announces loading progress", () => {
    render(<PageLoadingState label="Loading applications…" />);
    expect(screen.getByText("Loading applications…")).toBeVisible();
    expect(screen.getByText("Loading applications…").parentElement).toHaveAttribute("aria-live", "polite");
  });

  it("shows an accessible error and retries", async () => {
    const onRetry = vi.fn();
    render(<InlineErrorState title="Upload failed" message="Network unavailable" onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Network unavailable");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("renders an empty-state action", () => {
    render(<EmptyState title="No applications" message="Create the first one." action={<a href="/applications/new">New application</a>} />);
    expect(screen.getByRole("heading", { name: "No applications" })).toBeVisible();
    expect(screen.getByRole("link", { name: "New application" })).toHaveAttribute("href", "/applications/new");
  });
});
