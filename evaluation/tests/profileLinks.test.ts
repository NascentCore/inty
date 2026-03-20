import { describe, expect, it } from "vitest";

import {
  buildAgentProfilePageUrl,
  buildReportUserConversationsPageUrl,
  buildUserProfilePageUrl,
  getDeepLinkedAgentIdFromHash,
  getDeepLinkedReportIdFromHash,
  getDeepLinkedUserIdFromHash,
  parseEvaluationHashRoute,
} from "../utils/profileLinks";

describe("profileLinks utils", () => {
  it("builds deep links for agent and user profile pages", () => {
    const baseUrl = "https://ops.inty.cc/evaluation/";

    expect(buildAgentProfilePageUrl(baseUrl, "agent-1")).toBe(
      "https://ops.inty.cc/evaluation/#agents?agentId=agent-1",
    );
    expect(buildUserProfilePageUrl(baseUrl, "user-1")).toBe(
      "https://ops.inty.cc/evaluation/#user-daily-messages?userId=user-1",
    );
    expect(buildReportUserConversationsPageUrl(baseUrl, "report-1")).toBe(
      "https://ops.inty.cc/evaluation/#report-user-conversations?reportId=report-1",
    );
  });

  it("parses hash route and query parameters", () => {
    const parsed = parseEvaluationHashRoute("#agents?agentId=abc&foo=bar");

    expect(parsed.pageKey).toBe("agents");
    expect(parsed.params.get("agentId")).toBe("abc");
    expect(parsed.params.get("foo")).toBe("bar");
  });

  it("extracts deep linked ids only from matching pages", () => {
    expect(getDeepLinkedAgentIdFromHash("#agents?agentId=agent-100")).toBe(
      "agent-100",
    );
    expect(
      getDeepLinkedUserIdFromHash("#user-daily-messages?userId=user-100"),
    ).toBe("user-100");
    expect(
      getDeepLinkedReportIdFromHash(
        "#report-user-conversations?reportId=report-100",
      ),
    ).toBe("report-100");

    expect(getDeepLinkedAgentIdFromHash("#chat?agentId=agent-100")).toBe("");
    expect(getDeepLinkedUserIdFromHash("#agents?userId=user-100")).toBe("");
    expect(getDeepLinkedReportIdFromHash("#report-feedback?reportId=report-100")).toBe(
      "",
    );
  });
});
