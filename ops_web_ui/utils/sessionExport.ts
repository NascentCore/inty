import type { SessionMessageItem, UserSessionItem } from "../types";
import { formatUtcTime } from "./dateUtils";

interface BuildSessionExportContentParams {
  chatId: string;
  agentName: string;
  session: UserSessionItem;
  messages: SessionMessageItem[];
}

const isUserMessage = (messageType: string): boolean =>
  messageType === "human" || messageType === "HumanMessage";

export const buildSessionExportContent = ({
  chatId,
  agentName,
  session,
  messages,
}: BuildSessionExportContentParams): string => {
  const sortedMessages = [...messages].sort((a, b) => {
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    return timeA - timeB;
  });

  const lines: string[] = [];
  lines.push("会话导出记录");
  lines.push("====================");
  lines.push(`角色名称: ${agentName}`);
  lines.push(`角色形象图片链接: ${session.agent_avatar_url || "N/A"}`);
  lines.push(`会话ID: ${chatId}`);
  lines.push(`创建时间: ${formatUtcTime(session.created_at)}`);
  lines.push(`更新时间: ${formatUtcTime(session.updated_at)}`);
  lines.push(`消息总数: ${sortedMessages.length}`);
  lines.push("");
  lines.push("对话记录");
  lines.push("====================");
  lines.push("");

  sortedMessages.forEach((msg) => {
    const timestamp = formatUtcTime(msg.created_at);
    const sender = isUserMessage(msg.message_type) ? "👤 用户" : "🤖 AI";

    lines.push(`[${timestamp}] ${sender}`);
    lines.push("");

    if (msg.message_type === "image" && msg.image_url) {
      lines.push("[图片消息]");
      lines.push(`图片URL: ${msg.image_url}`);
    } else if (msg.content) {
      lines.push(msg.content);
    } else {
      lines.push("[无文本内容]");
    }

    if (msg.audio_url) {
      lines.push("");
      lines.push("[语音消息]");
      lines.push(`语音URL: ${msg.audio_url}`);
    }

    if (msg.meta_data?.generated_image?.image_url) {
      lines.push("");
      lines.push("[生成的图片]");
      lines.push(`图片URL: ${msg.meta_data.generated_image.image_url}`);
      if (
        msg.meta_data.generated_image.width &&
        msg.meta_data.generated_image.height
      ) {
        lines.push(
          `尺寸: ${msg.meta_data.generated_image.width} × ${msg.meta_data.generated_image.height}`,
        );
      }
    }

    lines.push("");
    lines.push("---");
    lines.push("");
  });

  return lines.join("\n");
};
