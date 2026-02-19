import { describe, expect, it } from "vitest";
import {
  GENERATED_IMAGE_COUNT_BADGE_OVERFLOW_COUNT,
  normalizeGeneratedImageCount,
} from "../utils/generatedImageCountDisplay";

describe("generatedImageCountDisplay", () => {
  it("keeps the real count value for large numbers", () => {
    expect(normalizeGeneratedImageCount(523)).toBe(523);
  });

  it("uses an overflow threshold larger than real counts", () => {
    expect(GENERATED_IMAGE_COUNT_BADGE_OVERFLOW_COUNT).toBeGreaterThan(523);
  });
});
