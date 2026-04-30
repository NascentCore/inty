import { describe, expect, it } from "vitest";

import type { UserAgentConversationItem, UserSessionItem } from "../types";
import {
  countUserAgentConversationMessages,
  countUserAgentConversationSessions,
  filterSessionsWithMessages,
  isUserMessageType,
} from "../utils/userAgentConversations";

describe("userAgentConversations", () => {
  it("detects user message type", () => {
    expect(isUserMessageType("human")).toBe(true);
    expect(isUserMessageType("HumanMessage")).toBe(true);
    expect(isUserMessageType("USER")).toBe(true);
    expect(isUserMessageType("ai")).toBe(false);
    expect(isUserMessageType(undefined)).toBe(false);
  });

  it("counts sessions and messages for one page", () => {
    const items: UserAgentConversationItem[] = [
      {
        user_id: "user-1",
        auth_type: "GOOGLE",
        user_created_at: null,
        nickname: "Alice",
        email: "alice@example.com",
        agent_id: "agent-1",
        agent_name: "Agent One",
        session_count: 2,
        message_count: 8,
        voice_message_count: 1,
        sessions: [],
      },
      {
        user_id: "user-2",
        auth_type: "GUEST",
        user_created_at: null,
        nickname: "Bob",
        email: null,
        agent_id: "agent-2",
        agent_name: "Agent Two",
        session_count: 1,
        message_count: 3,
        voice_message_count: 0,
        sessions: [],
      },
    ];

    expect(countUserAgentConversationSessions(items)).toBe(3);
    expect(countUserAgentConversationMessages(items)).toBe(11);
  });

  it("filterSessionsWithMessages omits zero message_count rows", () => {
    const sessions: UserSessionItem[] = [
      {
        chat_id: "c1",
        agent_name: "A",
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
        message_count: 0,
      },
      {
        chat_id: "c2",
        agent_name: "B",
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
        message_count: 3,
      },
    ];
    const filtered = filterSessionsWithMessages(sessions);
    expect(filtered).toHaveLength(1);
    expect(filtered[0].chat_id).toBe("c2");
  });
});
