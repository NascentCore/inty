import { describe, expect, it } from "vitest";
import type { ConversationsDetailResponse } from "../types";
import {
  buildAllUsersMessageRows,
  isUserMessageType,
} from "../utils/allUsersMessages";

describe("allUsersMessages", () => {
  it("detects user message types", () => {
    expect(isUserMessageType("human")).toBe(true);
    expect(isUserMessageType("HumanMessage")).toBe(true);
    expect(isUserMessageType("USER")).toBe(true);
    expect(isUserMessageType("ai")).toBe(false);
    expect(isUserMessageType("AIMessage")).toBe(false);
    expect(isUserMessageType(undefined)).toBe(false);
    expect(isUserMessageType(null)).toBe(false);
  });

  it("flattens and sorts all users messages", () => {
    const conversations: ConversationsDetailResponse[] = [
      {
        user_id: "user-1",
        auth_type: "GOOGLE",
        user_created_at: null,
        nickname: "alice",
        email: "alice@example.com",
        sessions: [
          {
            chat_id: "chat-1",
            agent_name: "Agent A",
            message_count: 2,
            voice_message_count: 0,
            messages: [
              {
                chat_id: "chat-1",
                message_type: "human",
                content: "hello",
                created_at: "2026-03-13T01:00:00+00:00",
                audio_url: null,
              },
              {
                chat_id: "chat-1",
                message_type: "ai",
                content: "hi",
                created_at: "2026-03-13T01:01:00+00:00",
                audio_url: null,
              },
            ],
          },
        ],
      },
      {
        user_id: "user-2",
        auth_type: "GOOGLE",
        user_created_at: null,
        nickname: "bob",
        email: "bob@example.com",
        sessions: [
          {
            chat_id: "chat-2",
            agent_name: "Agent B",
            message_count: 1,
            voice_message_count: 0,
            messages: [
              {
                chat_id: "chat-2",
                message_type: "HumanMessage",
                content: "morning",
                created_at: "2026-03-13T02:00:00+00:00",
                audio_url: null,
              },
            ],
          },
        ],
      },
    ];

    const rows = buildAllUsersMessageRows(conversations);
    expect(rows).toHaveLength(3);
    expect(rows[0].user_id).toBe("user-2");
    expect(rows[0].sender_type).toBe("USER");
    expect(rows[1].sender_type).toBe("AI");
    expect(rows[2].sender_type).toBe("USER");
  });
});
