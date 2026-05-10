import { describe, expect, it } from "vitest";
import { shouldShowSingleSelectorEmptySearch } from "../utils/singleAgentSelector";

describe("singleAgentSelector utils", () => {
  it("shows search empty state only when query exists and no match", () => {
    expect(shouldShowSingleSelectorEmptySearch(3, "abc", 0)).toBe(true);
    expect(shouldShowSingleSelectorEmptySearch(3, " ", 0)).toBe(false);
    expect(shouldShowSingleSelectorEmptySearch(0, "abc", 0)).toBe(false);
    expect(shouldShowSingleSelectorEmptySearch(3, "abc", 1)).toBe(false);
  });
});
