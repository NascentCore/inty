/**
 * Gemini 聊天与情绪解析服务（最小实现）
 * 使用 REST API 调用 Gemini 并让其输出 JSON: { reply: string, emotion: Emotion }
 */

export type Emotion =
  | "Neutral"
  | "Happy"
  | "Sad"
  | "Angry"
  | "Surprised"
  | "Fearful"
  | "Disgusted"
  | "Shy"
  | "Confused"
  | "Excited"
  | "Bored"
  | "Tired"
  | "Loving"
  | "Proud"
  | "Embarrassed"
  | "Lonely"
  | "Anxious"
  | "Calm"
  | "Curious"
  | "Determined";

export const EMOTIONS: Emotion[] = [
  "Neutral",
  "Happy",
  "Sad",
  "Angry",
  "Surprised",
  "Fearful",
  "Disgusted",
  "Shy",
  "Confused",
  "Excited",
  "Bored",
  "Tired",
  "Loving",
  "Proud",
  "Embarrassed",
  "Lonely",
  "Anxious",
  "Calm",
  "Curious",
  "Determined",
];

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

export interface GeminiReplyResult {
  reply: string;
  emotion: Emotion;
}

const MODEL = "gemini-2.5-flash-latest"; // 轻量快速，足以驱动情绪选择
const API_BASE = "https://generativelanguage.googleapis.com/v1beta";

function buildSystemPrompt(): string {
  return [
    "你是一个Live2D角色情绪控制器与对话助手。",
    "要求：每次回答时，必须从以下情绪列表中挑选最合适的一个，并严格按JSON输出。",
    `可用情绪列表: ${EMOTIONS.join(", ")}`,
    "输出格式为严格的JSON，不包含多余文字或代码块围栏：",
    '{"reply": "<给用户的自然语言回复>", "emotion": "<从上述列表里选一个>"}',
    "禁止输出任何解释、前后缀、Markdown代码块或额外字段。",
  ].join("\n");
}

function buildUserPrompt(
  history: ChatHistoryItem[],
  userInput: string,
): string {
  const historyText = history
    .slice(-10)
    .map((m) =>
      m.role === "user" ? `用户: ${m.content}` : `助手: ${m.content}`,
    )
    .join("\n");
  const scene =
    "现在请基于对话上下文，给出本轮回复 reply，并选择最贴合的 emotion（仅从列表中选一个）。";
  return [historyText, `用户: ${userInput}`, scene]
    .filter(Boolean)
    .join("\n\n");
}

function extractJson(text: string): any | null {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {}
  const fenceMatch = text.match(/\{[\s\S]*\}/);
  if (fenceMatch) {
    try {
      return JSON.parse(fenceMatch[0]);
    } catch {}
  }
  return null;
}

export async function generateReplyWithEmotion(
  apiKey: string,
  history: ChatHistoryItem[],
  userInput: string,
): Promise<GeminiReplyResult> {
  if (!apiKey) {
    throw new Error("缺少 Gemini API Key");
  }

  const url = `${API_BASE}/models/${MODEL}:generateContent?key=${encodeURIComponent(apiKey)}`;

  const systemPrompt = buildSystemPrompt();
  const userPrompt = buildUserPrompt(history, userInput);

  const body = {
    contents: [
      { role: "user", parts: [{ text: systemPrompt }] },
      { role: "user", parts: [{ text: userPrompt }] },
    ],
    generationConfig: { temperature: 0.6, maxOutputTokens: 512 },
  } as const;

  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const detail = await resp.text().catch(() => "");
    throw new Error(
      `Gemini 调用失败: HTTP ${resp.status} ${resp.statusText} ${detail}`,
    );
  }

  const data = await resp.json();
  const text: string =
    data?.candidates?.[0]?.content?.parts?.[0]?.text ??
    '{"reply": "抱歉，我现在无法回复。", "emotion": "Neutral"}';

  const parsed = extractJson(text);
  if (parsed && typeof parsed === "object") {
    const emotionCandidate = String(parsed.emotion || "");
    const normalized = (emotionCandidate.charAt(0).toUpperCase() +
      emotionCandidate.slice(1)) as Emotion;
    const isValid = EMOTIONS.includes(normalized);
    return {
      reply: String(parsed.reply || "(无内容)"),
      emotion: isValid ? normalized : ("Neutral" as Emotion),
    };
  }

  return { reply: String(text || "(无内容)"), emotion: "Neutral" };
}
