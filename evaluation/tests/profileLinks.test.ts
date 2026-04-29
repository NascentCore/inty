import { describe, expect, it } from "vitest";

import {
  buildAgentProfilePageUrl,
  buildReportUserConversationsPageUrl,
  buildUserProfilePageUrl,
  buildVoiceRecordingPageUrl,
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
    const recordingUrl = buildVoiceRecordingPageUrl(baseUrl, {
      audioUrl: "https://storage.googleapis.com/inty-static/live_chat/u1/a1/x.wav",
      userId: "user-1",
      agentId: "agent-1",
      agentName: "Salem",
      createdAt: "2026-04-28T12:00:00Z",
      durationSeconds: 24.5,
      messageId: 42,
    });
    expect(recordingUrl).toContain("#voice-recording?");
    expect(recordingUrl).toContain("userId=user-1");
    expect(recordingUrl).toContain("agentId=agent-1");
    expect(recordingUrl).toContain("messageId=42");
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
    expect(
      getDeepLinkedReportIdFromHash("#report-feedback?reportId=report-100"),
    ).toBe("");
  });
});
