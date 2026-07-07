import { describe, expect, it } from "vitest";

import {
  sessionMessagesPaginationProps,
  shouldShowSessionMessagesPagination,
} from "../utils/sessionMessagesPagination";

describe("sessionMessagesPagination utils", () => {
  it("shows pagination when there are more pages", () => {
    expect(
      shouldShowSessionMessagesPagination({
        has_more: true,
        page: 1,
        size: 50,
        total: 50,
      }),
    ).toBe(true);
  });

  it("keeps pagination on later pages for direct back/forward jump", () => {
    expect(
      shouldShowSessionMessagesPagination({
        has_more: false,
        page: 3,
        size: 50,
        total: 120,
      }),
    ).toBe(true);
  });

  it("shows pagination when total exceeds single page size", () => {
    expect(
      shouldShowSessionMessagesPagination({
        has_more: false,
        page: 1,
        size: 50,
        total: 51,
      }),
    ).toBe(true);
  });

  it("hides pagination on single-page result", () => {
    expect(
      shouldShowSessionMessagesPagination({
        has_more: false,
        page: 1,
        size: 50,
        total: 50,
      }),
    ).toBe(false);
  });

  it("enables quick jump in pagination props", () => {
    expect(sessionMessagesPaginationProps.showSizeChanger).toBe(false);
    expect(sessionMessagesPaginationProps.showQuickJumper).toBe(true);
    expect(sessionMessagesPaginationProps.showLessItems).toBe(true);
  });
});
