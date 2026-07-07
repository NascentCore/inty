import { describe, expect, it } from "vitest";

import { buildImageFeedbackTargetId } from "../utils/imageFeedbackReport";

describe("imageFeedbackReport", () => {
  it("builds stable short target id for same image url", () => {
    const imageUrl = "https://cdn.example.com/inty-test/chat_images/abc.jpg";
    const first = buildImageFeedbackTargetId(imageUrl);
    const second = buildImageFeedbackTargetId(imageUrl);
    expect(first).toBe(second);
    expect(first.startsWith("IMAGE_FEEDBACK_")).toBe(true);
    expect(first.length).toBeLessThanOrEqual(100);
  });
});
