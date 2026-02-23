/**
 * CREATED_BY_AGENT
 */
import { describe, expect, it } from "vitest";
import { USER_ANALYTICS_GENERATED_IMAGE_PREVIEW_STYLE } from "../utils/userAnalyticsReportImagePreview";

describe("userAnalyticsReportImagePreview", () => {
  it("uses contain so generated images are fully visible", () => {
    expect(USER_ANALYTICS_GENERATED_IMAGE_PREVIEW_STYLE.objectFit).toBe(
      "contain",
    );
  });

  it("keeps square image thumbnails", () => {
    expect(USER_ANALYTICS_GENERATED_IMAGE_PREVIEW_STYLE.aspectRatio).toBe(
      "1 / 1",
    );
  });
});
