import { describe, expect, it } from "vitest";

import { userDisplayId } from "../utils/userDisplayId";

describe("userDisplayId", () => {
  it("returns readable_id when set", () => {
    expect(
      userDisplayId({ id: "user-abc", readable_id: "12345678" }),
    ).toBe("12345678");
  });

  it("falls back to id when readable_id is null or blank", () => {
    expect(userDisplayId({ id: "user-abc", readable_id: null })).toBe(
      "user-abc",
    );
    expect(userDisplayId({ id: "user-abc", readable_id: "  " })).toBe(
      "user-abc",
    );
    expect(userDisplayId({ id: "user-abc" })).toBe("user-abc");
  });
});
