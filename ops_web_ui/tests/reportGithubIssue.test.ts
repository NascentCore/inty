import { describe, expect, it } from "vitest";

import {
  isValidGithubIssueUrl,
  normalizeGithubIssueUrlInput,
} from "../utils/reportGithubIssue";

describe("reportGithubIssue utils", () => {
  it("normalizes empty input to null", () => {
    expect(normalizeGithubIssueUrlInput("   ")).toBeNull();
  });

  it("trims valid input", () => {
    expect(
      normalizeGithubIssueUrlInput(
        " https://github.com/example/repo/issues/123 ",
      ),
    ).toBe("https://github.com/example/repo/issues/123");
  });

  it("validates github issue url format", () => {
    expect(
      isValidGithubIssueUrl("https://github.com/example/repo/issues/123"),
    ).toBe(true);
    expect(isValidGithubIssueUrl("https://example.com/repo/issues/123")).toBe(
      false,
    );
    expect(
      isValidGithubIssueUrl("https://github.com/example/repo/pull/123"),
    ).toBe(false);
  });
});
