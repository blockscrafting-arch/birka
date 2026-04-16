import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ErrorBoundary } from "../components/ui/ErrorBoundary";

// Suppress console.error for expected error boundary logs
const originalError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});
afterEach(() => {
  console.error = originalError;
});

const ThrowingComponent = (): never => {
  throw new Error("Test render error");
};

const SafeComponent = (): JSX.Element => <div>Дети рендерятся</div>;

describe("ErrorBoundary", () => {
  it("catches child render error and shows fallback UI", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/что-то пошло не так/i)).toBeInTheDocument();
  });

  it("renders children normally when no error", () => {
    render(
      <ErrorBoundary>
        <SafeComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText("Дети рендерятся")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
