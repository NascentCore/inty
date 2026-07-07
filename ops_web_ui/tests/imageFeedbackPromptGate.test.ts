import { describe, expect, it } from "vitest";

import {
  shouldShowImageFeedbackPrompt,
  toLocalCalendarDateKey,
} from "../utils/imageFeedbackPromptGate";

describe("imageFeedbackPromptGate", () => {
  it("builds local calendar date key", () => {
    const date = new Date("2026-03-08T18:32:15");
    expect(toLocalCalendarDateKey(date)).toBe("2026-03-08");
  });

  it("returns false when already shown on same local day", () => {
    const now = new Date("2026-03-08T23:59:59");
    expect(shouldShowImageFeedbackPrompt("2026-03-08", now)).toBe(false);
  });

  it("returns true when day changed", () => {
    const now = new Date("2026-03-09T00:00:01");
    expect(shouldShowImageFeedbackPrompt("2026-03-08", now)).toBe(true);
  });
});
