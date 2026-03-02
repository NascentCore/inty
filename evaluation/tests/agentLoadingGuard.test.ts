import { describe, expect, it } from "vitest";
import { shouldLoadAgentsOnPageEnter } from "../utils/agentLoadingGuard";

describe("shouldLoadAgentsOnPageEnter", () => {
  it("returns true before first load when list is empty", () => {
    expect(
      shouldLoadAgentsOnPageEnter({
        hasLoaded: false,
        isLoading: false,
        agentsCount: 0,
      }),
    ).toBe(true);
  });

  it("returns false after agents have been loaded", () => {
    expect(
      shouldLoadAgentsOnPageEnter({
        hasLoaded: true,
        isLoading: false,
        agentsCount: 0,
      }),
    ).toBe(false);
  });

  it("returns false while loading is in progress", () => {
    expect(
      shouldLoadAgentsOnPageEnter({
        hasLoaded: false,
        isLoading: true,
        agentsCount: 0,
      }),
    ).toBe(false);
  });

  it("returns false when list already has data", () => {
    expect(
      shouldLoadAgentsOnPageEnter({
        hasLoaded: false,
        isLoading: false,
        agentsCount: 12,
      }),
    ).toBe(false);
  });
});
