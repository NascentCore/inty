import { describe, it, expect } from "vitest";
import { getEmotionBackgroundUrl } from "../services/emotionBackgrounds";
import { EMOTIONS } from "../services/gemini";

describe("emotionBackgrounds", () => {
  it("returns data URI for each emotion", () => {
    for (const e of EMOTIONS) {
      const url = getEmotionBackgroundUrl(e);
      expect(url.startsWith("data:image/svg+xml")).toBe(true);
      expect(url.length).toBeGreaterThan(20);
    }
  });

  it("falls back to Neutral for unknown", () => {
    // @ts-expect-error test fallback
    const url = getEmotionBackgroundUrl("NotAnEmotion");
    expect(url.startsWith("data:image/svg+xml")).toBe(true);
  });
});
