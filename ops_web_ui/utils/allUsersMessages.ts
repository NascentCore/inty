import type {
  ChatMessageResponse,
  ConversationsDetailResponse,
} from "../types";
import { isUserMessageType } from "./messageTypes";

export { isUserMessageType } from "./messageTypes";

export interface AllUsersMessageRow {
  key: string;
  user_id: string;
  email: string | null;
  nickname: string | null;
  chat_id: string;
  agent_name: string;
  message_type: string;
  sender_type: "USER" | "AI";
  content: string;
  created_at: string | null;
}

const buildMessageKey = (
  userId: string,
  chatId: string,
  message: ChatMessageResponse,
  index: number,
): string => {
  const createdAt = message.created_at ?? "no-time";
  const type = message.message_type ?? "unknown-type";
  return `${userId}-${chatId}-${createdAt}-${type}-${index}`;
};

export const buildAllUsersMessageRows = (
  conversations: ConversationsDetailResponse[],
): AllUsersMessageRow[] => {
  const rows: AllUsersMessageRow[] = [];

  conversations.forEach((userConversation) => {
    userConversation.sessions.forEach((session) => {
      session.messages.forEach((message, index) => {
        const isUser = isUserMessageType(message.message_type);
        rows.push({
          key: buildMessageKey(
            userConversation.user_id,
            session.chat_id,
            message,
            index,
          ),
          user_id: userConversation.user_id,
          email: userConversation.email,
          nickname: userConversation.nickname,
          chat_id: session.chat_id,
          agent_name: session.agent_name,
          message_type: message.message_type ?? "unknown",
          sender_type: isUser ? "USER" : "AI",
          content: message.content ?? "",
          created_at: message.created_at,
        });
      });
    });
  });

  rows.sort((first, second) => {
    if (!first.created_at && !second.created_at) {
      return 0;
    }
    if (!first.created_at) {
      return 1;
    }
    if (!second.created_at) {
      return -1;
    }
    return (
      new Date(second.created_at).getTime() -
      new Date(first.created_at).getTime()
    );
  });

  return rows;
};
