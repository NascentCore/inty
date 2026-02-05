/**
 * CREATED_BY_AGENT
 */
import { describe, it, expect } from "vitest";
import {
  REPORT_IMAGE_PREVIEW_SIZE,
  REPORT_IMAGE_PREVIEW_STYLE,
} from "../utils/reportImagePreview";

describe("report image preview", () => {
  it("uses contain to avoid cropping", () => {
    expect(REPORT_IMAGE_PREVIEW_STYLE.objectFit).toBe("contain");
  });

  it("has a positive size", () => {
    expect(REPORT_IMAGE_PREVIEW_SIZE).toBeGreaterThan(0);
  });
});
