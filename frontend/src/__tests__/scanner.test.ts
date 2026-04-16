import { describe, expect, it } from "vitest";

import {
  CAMERA_ERROR_NOT_FOUND,
  CAMERA_ERROR_PERMISSION,
  CAMERA_ERROR_NOT_READABLE,
  SCANNER_ERROR_PREFIX,
  getCameraErrorMessage,
  isScanFrameError,
} from "../constants/scanner";

describe("isScanFrameError", () => {
  it("returns true for frame errors (no code in frame)", () => {
    expect(isScanFrameError("No barcode or QR code detected.")).toBe(true);
    expect(
      isScanFrameError("QR code parse error, error = No barcode or QR code detected."),
    ).toBe(true);
    expect(isScanFrameError("QR code parse error, error = NotFoundException")).toBe(true);
    expect(isScanFrameError("No QR code detected")).toBe(true);
    expect(isScanFrameError("something not detected in frame")).toBe(true);
  });

  it("returns false for real camera/access errors", () => {
    expect(isScanFrameError("NotAllowedError")).toBe(false);
    expect(isScanFrameError("Permission denied")).toBe(false);
    expect(isScanFrameError("NotFoundError")).toBe(false);
    expect(isScanFrameError("NotReadableError")).toBe(false);
    expect(
      isScanFrameError("Error getting userMedia, error = NotFoundError"),
    ).toBe(false);
    expect(isScanFrameError("Camera streaming not supported")).toBe(false);
    expect(isScanFrameError("No camera found")).toBe(false);
    expect(isScanFrameError("insecure context")).toBe(false);
  });

  it("returns false for empty or whitespace-only input", () => {
    expect(isScanFrameError("")).toBe(false);
    expect(isScanFrameError("   ")).toBe(false);
  });

  it("treats NotFoundException as frame error but NotFoundError as real error", () => {
    expect(isScanFrameError("NotFoundException")).toBe(true);
    expect(isScanFrameError("NotFoundError")).toBe(false);
  });

  it("returns false for camera-not-found variants (show to user)", () => {
    expect(isScanFrameError("No cameras found")).toBe(false);
    expect(isScanFrameError("Camera not found")).toBe(false);
  });
});

describe("getCameraErrorMessage", () => {
  it("maps permission errors to CAMERA_ERROR_PERMISSION", () => {
    expect(getCameraErrorMessage("NotAllowedError")).toBe(CAMERA_ERROR_PERMISSION);
    expect(getCameraErrorMessage("Permission denied")).toBe(CAMERA_ERROR_PERMISSION);
    expect(getCameraErrorMessage("NotAllowed")).toBe(CAMERA_ERROR_PERMISSION);
  });

  it("maps NotFoundError to CAMERA_ERROR_NOT_FOUND (not NotFoundException)", () => {
    expect(getCameraErrorMessage("NotFoundError")).toBe(CAMERA_ERROR_NOT_FOUND);
    expect(
      getCameraErrorMessage("Error getting userMedia, error = NotFoundError"),
    ).toBe(CAMERA_ERROR_NOT_FOUND);
    expect(getCameraErrorMessage("QR code parse error, error = NotFoundException")).not.toBe(
      CAMERA_ERROR_NOT_FOUND,
    );
    expect(
      getCameraErrorMessage("QR code parse error, error = NotFoundException"),
    ).toContain(SCANNER_ERROR_PREFIX);
  });

  it("maps NotReadable errors to CAMERA_ERROR_NOT_READABLE", () => {
    expect(getCameraErrorMessage("NotReadableError")).toBe(CAMERA_ERROR_NOT_READABLE);
    expect(getCameraErrorMessage("NotReadable")).toBe(CAMERA_ERROR_NOT_READABLE);
  });

  it("returns generic prefix for unknown messages", () => {
    const unknown = "Some unknown error";
    expect(getCameraErrorMessage(unknown)).toContain(SCANNER_ERROR_PREFIX);
    expect(getCameraErrorMessage(unknown)).toContain("Some unknown error");
  });

  it("returns SCANNER_ERROR_PREFIX for empty string", () => {
    expect(getCameraErrorMessage("")).toBe(SCANNER_ERROR_PREFIX);
  });
});
