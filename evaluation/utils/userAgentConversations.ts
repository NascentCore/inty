import type { UserAgentConversationItem, UserSessionItem } from "../types";

const USER_MESSAGE_TYPES = new Set(["human", "HumanMessage", "user", "USER"]);

export const isUserMessageType = (
  messageType: string | null | undefined,
): boolean => {
  if (!messageType) {
    return false;
  }
  return USER_MESSAGE_TYPES.has(messageType);
};

export const countUserAgentConversationSessions = (
  items: UserAgentConversationItem[],
): number =>
  items.reduce(
    (sessionCount, groupedConversation) =>
      sessionCount + groupedConversation.session_count,
    0,
  );

export const countUserAgentConversationMessages = (
  items: UserAgentConversationItem[],
): number =>
  items.reduce(
    (messageCount, groupedConversation) =>
      messageCount + groupedConversation.message_count,
    0,
  );

export const filterSessionsWithMessages = (
  sessions: UserSessionItem[],
): UserSessionItem[] =>
  sessions.filter((s) => (s.message_count ?? 0) > 0);

