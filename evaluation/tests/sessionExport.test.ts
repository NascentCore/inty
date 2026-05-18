import { describe, expect, it } from "vitest";

import type { SessionMessageItem, UserSessionItem } from "../types";
import { buildSessionExportContent } from "../utils/sessionExport";

const baseSession: UserSessionItem = {
  chat_id: "chat-123",
  agent_id: "agent-uuid-1",
  agent_name: "Amber",
  agent_avatar_url: null,
  created_at: "2026-03-16T21:16:22Z",
  updated_at: "2026-03-16T21:50:27Z",
  message_count: 2,
};

const baseMessages: SessionMessageItem[] = [
  {
    id: 1,
    message_type: "human",
    content: "hello",
    created_at: "2026-03-16T21:17:27Z",
    audio_url: null,
    meta_data: null,
  },
  {
    id: 2,
    message_type: "ai",
    content: "hi",
    created_at: "2026-03-16T21:17:28Z",
    audio_url: null,
    meta_data: null,
  },
];

describe("sessionExport utils", () => {
  it("includes role avatar link in exported content", () => {
    const content = buildSessionExportContent({
      chatId: "chat-123",
      agentName: "Amber",
      session: {
        ...baseSession,
        agent_avatar_url: "https://cdn.example.com/agents/amber-avatar.webp",
      },
      messages: baseMessages,
    });

    expect(content).toContain(
      "角色形象图片链接: https://cdn.example.com/agents/amber-avatar.webp",
    );
  });

  it("uses N/A when role avatar link is missing", () => {
    const content = buildSessionExportContent({
      chatId: "chat-123",
      agentName: "Amber",
      session: baseSession,
      messages: baseMessages,
    });

    expect(content).toContain("角色形象图片链接: N/A");
  });
});
