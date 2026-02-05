import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "../components/ui/Button";

describe("Button", () => {
  it("renders and handles click", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Нажмите</Button>);
    fireEvent.click(screen.getByText("Нажмите"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
