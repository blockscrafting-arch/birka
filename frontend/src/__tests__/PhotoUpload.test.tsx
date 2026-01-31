import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PhotoUpload } from "../components/shared/PhotoUpload";

describe("PhotoUpload", () => {
  it("calls onFileChange", () => {
    const onFileChange = vi.fn();
    render(<PhotoUpload onFileChange={onFileChange} />);
    const input = screen.getByLabelText("Добавить фото") as HTMLInputElement;
    const file = new File(["test"], "test.jpg", { type: "image/jpeg" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(onFileChange).toHaveBeenCalledTimes(1);
  });
});
