import type { UserAgentConversationItem, UserSessionItem } from "../types";

export { isUserMessageType } from "./messageTypes";

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
): UserSessionItem[] => sessions.filter((s) => (s.message_count ?? 0) > 0);
