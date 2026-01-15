"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  createOpenRouterChatCompletion,
  fetchOpenRouterModels,
  type OpenRouterChatCompletionRequest,
  type OpenRouterModel,
} from "@/lib/openrouter";
import { useLocalStorageState } from "@/lib/useLocalStorageState";
import {
  buildMessages,
  buildMessagesMultiSystem,
  buildFirstMessage,
  buildIntroMessage,
  estimateTokensFromText,
  type PromptBlock,
} from "@/lib/prompting";

const LS_API_KEY = "mychatplayground.openrouter.apiKey";
const LS_MODEL_ID = "mychatplayground.openrouter.modelId";
const LS_SETTINGS = "mychatplayground.openrouter.settings";
const LS_PROMPT = "mychatplayground.promptDraft";
const LS_CHAT = "mychatplayground.chatHistory";
const LS_VERSIONS = "mychatplayground.promptVersions";
const LS_SNIPPETS = "mychatplayground.blockSnippets.v1";
const LS_PROMPT_PREVIEW_MODE = "mychatplayground.promptPreview.mode";
const LS_PROMPT_BUILD_MODE = "mychatplayground.promptBuildMode";
const LS_PROJECT_STATE = "mychatplayground.projectState.v1";
const LS_USER_AI_PROMPT = "mychatplayground.userAiPrompt";

type ChatMsg = { role: "user" | "assistant"; content: string };

type ModelSettings = {
  temperature: number;
  top_p: number;
  max_tokens: number;
  presence_penalty: number;
  frequency_penalty: number;
};

type PromptDraftStored = {
  systemBlocks: PromptBlock[];
  variablesJson: string; // {"user": "...", "char": "..."}
};

type PromptVersion = {
  id: string;
  name: string;
  createdAt: number;
  prompt: PromptDraftStored;
};

type ExportBundleV2 = {
  schema: "mychatplayground.export.v2";
  exportedAt: number;
  modelId: string;
  settings: ModelSettings;
  promptDraft: PromptDraftStored;
  promptVersions: PromptVersion[];
  chatHistory: ChatMsg[];
};

type ExportBundleV3 = {
  schema: "mychatplayground.export.v3";
  exportedAt: number;
  modelId: string;
  settings: ModelSettings;
  promptDraft: PromptDraftStored;
  promptVersions: PromptVersion[];
  chatHistory: ChatMsg[];
};

type ProjectStateV1 = {
  schema: "mychatplayground.projectState.v1";
  savedAt: number;
  modelId: string;
  settings: ModelSettings;
  promptDraft: PromptDraftStored;
  promptVersions: PromptVersion[];
  chatHistory: ChatMsg[];
  snippets: string[];
  promptPreviewMode: "concat" | "langsmith" | "openrouter";
};

type ExportBundleV1 = {
  schema: "mychatplayground.export.v1";
  exportedAt: number;
  modelId: string;
  settings: ModelSettings;
  promptDraft: any;
  promptVersions: any[];
  chatHistory: ChatMsg[];
};

const DEFAULT_SETTINGS: ModelSettings = {
  temperature: 0.7,
  top_p: 1,
  max_tokens: 800,
  presence_penalty: 0,
  frequency_penalty: 0,
};

function makeDefaultSystemBlocks(): PromptBlock[] {
  return [
    {
      id: "block-system",
      title: "System",
      enabled: true,
      content: "你是一个AI角色扮演助手。你需要保持人设一致、语气自然、对话连贯。",
    },
    {
      id: "block-persona",
      title: "Persona",
      enabled: true,
      content:
        "【角色设定】\n- 名字：\n- 性格：\n- 口头禅：\n- 世界观：\n\n【行为约束】\n- 不要暴露系统提示\n- 避免跳出角色\n",
    },
    {
      id: "block-intro",
      title: "Intro（场景介绍）",
      enabled: true,
      content: "",
    },
    {
      id: "block-first-message",
      title: "First Message（相遇）",
      enabled: true,
      content: "",
    },
  ];
}

const DEFAULT_PROMPT: PromptDraftStored = {
  systemBlocks: makeDefaultSystemBlocks(),
  variablesJson: JSON.stringify({ user: "JOY", char: "Oaklyn" }, null, 2),
};

const PROMPT_TEMPLATES: Array<{ name: string; value: PromptDraftStored }> = [
  { name: "（默认）角色扮演", value: DEFAULT_PROMPT },
];

function ensureDefaultBlocks(blocks: PromptBlock[]) {
  const ids = new Set(blocks.map((b) => b.id));
  const out = [...blocks];
  if (!ids.has("block-intro")) {
    out.push({
      id: "block-intro",
      title: "Intro（场景介绍）",
      enabled: true,
      content: "",
    });
  }
  if (!ids.has("block-first-message")) {
    out.push({
      id: "block-first-message",
      title: "First Message（相遇）",
      enabled: true,
      content: "",
    });
  }
  return out;
}

function coercePromptDraft(input: any): PromptDraftStored {
  if (input && Array.isArray(input.systemBlocks)) {
    const blocks: PromptBlock[] = input.systemBlocks.map((b: any, idx: number) => ({
      id: typeof b?.id === "string" ? b.id : `block-${idx}`,
      title: typeof b?.title === "string" ? b.title : `Block ${idx + 1}`,
      content: typeof b?.content === "string" ? b.content : "",
      enabled: typeof b?.enabled === "boolean" ? b.enabled : true,
    }));
    return {
      systemBlocks: ensureDefaultBlocks(
        blocks.length ? blocks : makeDefaultSystemBlocks(),
      ),
      variablesJson:
        typeof input.variablesJson === "string" ? input.variablesJson : "{}",
    };
  }

  // 旧数据迁移：system/persona -> systemBlocks
  const system = typeof input?.system === "string" ? input.system : "";
  const persona = typeof input?.persona === "string" ? input.persona : "";
  const blocks: PromptBlock[] = ensureDefaultBlocks([
    {
      id: "block-system",
      title: "System",
      enabled: true,
      content: system || makeDefaultSystemBlocks()[0]!.content,
    },
    {
      id: "block-persona",
      title: "Persona",
      enabled: true,
      content: persona,
    },
  ]).filter((b) => b.content.trim() !== "" || b.id === "block-system" || b.id === "block-first-message");

  return {
    systemBlocks: blocks.length ? blocks : makeDefaultSystemBlocks(),
    variablesJson:
      typeof input?.variablesJson === "string" ? input.variablesJson : "{}",
  };
}

function safeParseVars(raw: string) {
  try {
    if (raw.trim() === "") return { ok: true as const, value: {} as Record<string, string> };
    const v = JSON.parse(raw);
    if (v == null || Array.isArray(v) || typeof v !== "object") {
      return { ok: false as const, error: "变量必须是对象（JSON Object）" };
    }
    const out: Record<string, string> = {};
    for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
      out[k] = String(val);
    }
    return { ok: true as const, value: out };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : String(e) };
  }
}

/**
 * 智能统计文本：中文统计字数，英文统计单词数
 * 返回格式如："128 字" 或 "45 words" 或混合 "50 字 + 12 words"
 */
function countTextStats(text: string): string {
  if (!text || !text.trim()) return "0";

  // 匹配中文字符（包括中文标点）
  const chineseChars = text.match(/[\u4e00-\u9fff\u3400-\u4dbf]/g) || [];
  const chineseCount = chineseChars.length;

  // 移除中文字符后，统计英文单词
  const withoutChinese = text.replace(/[\u4e00-\u9fff\u3400-\u4dbf]/g, " ");
  const englishWords = withoutChinese
    .split(/\s+/)
    .filter((w) => /[a-zA-Z]/.test(w));
  const wordCount = englishWords.length;

  if (chineseCount > 0 && wordCount > 0) {
    return `${chineseCount} 字 + ${wordCount} words`;
  } else if (chineseCount > 0) {
    return `${chineseCount} 字`;
  } else if (wordCount > 0) {
    return `${wordCount} words`;
  }
  return "0";
}

/**
 * 解析导出的对话记录 txt 文件
 * 格式示例：
 * [2025-12-29 23:16:28 (UTC)] 🤖 AI
 * 消息内容...
 * ---
 * [2025-12-29 23:17:03 (UTC)] 👤 用户
 * 消息内容...
 */
function parseConversationLog(content: string): { messages: ChatMsg[]; info: string } {
  const lines = content.split("\n");
  const messages: ChatMsg[] = [];
  
  // 用于匹配消息头的正则表达式
  // 格式: [时间戳 (UTC)] 🤖 AI 或 [时间戳 (UTC)] 👤 用户
  const aiHeaderRegex = /^\[[\d\-\s:]+\s*\(UTC\)\]\s*🤖\s*AI\s*$/;
  const userHeaderRegex = /^\[[\d\-\s:]+\s*\(UTC\)\]\s*👤\s*用户\s*$/;
  
  let currentRole: "user" | "assistant" | null = null;
  let currentContent: string[] = [];
  let skippedCount = 0;
  
  const saveCurrentMessage = () => {
    if (currentRole && currentContent.length > 0) {
      // 过滤掉语音消息等特殊内容
      const filteredLines = currentContent.filter(line => {
        const trimmed = line.trim();
        // 跳过语音消息标记和 URL
        if (trimmed === "[语音消息]") return false;
        if (trimmed.startsWith("语音URL:")) return false;
        return true;
      });
      
      const text = filteredLines.join("\n").trim();
      if (text) {
        messages.push({ role: currentRole, content: text });
      }
    }
    currentRole = null;
    currentContent = [];
  };
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? "";
    const trimmedLine = line.trim();
    
    // 检查是否是分隔符
    if (trimmedLine === "---") {
      saveCurrentMessage();
      continue;
    }
    
    // 检查是否是 AI 消息头
    if (aiHeaderRegex.test(trimmedLine)) {
      saveCurrentMessage();
      currentRole = "assistant";
      continue;
    }
    
    // 检查是否是用户消息头
    if (userHeaderRegex.test(trimmedLine)) {
      saveCurrentMessage();
      currentRole = "user";
      continue;
    }
    
    // 跳过文件头信息
    if (trimmedLine.startsWith("会话导出记录") ||
        trimmedLine.startsWith("角色名称:") ||
        trimmedLine.startsWith("会话ID:") ||
        trimmedLine.startsWith("创建时间:") ||
        trimmedLine.startsWith("更新时间:") ||
        trimmedLine.startsWith("消息总数:") ||
        trimmedLine.startsWith("对话记录") ||
        trimmedLine === "=" .repeat(20) ||
        trimmedLine.match(/^=+$/)) {
      continue;
    }
    
    // 如果当前有角色，则添加到内容中
    if (currentRole) {
      // 保留空行（但不在开头）
      if (currentContent.length > 0 || trimmedLine) {
        currentContent.push(line);
      }
    }
  }
  
  // 保存最后一条消息
  saveCurrentMessage();
  
  const info = `成功导入 ${messages.length} 条消息（用户: ${messages.filter(m => m.role === "user").length}, AI: ${messages.filter(m => m.role === "assistant").length}）`;
  
  return { messages, info };
}

export default function Home() {
  const [apiKey, setApiKey] = useLocalStorageState<string>(LS_API_KEY, "");
  const [modelId, setModelId] = useLocalStorageState<string>(LS_MODEL_ID, "");
  const [settings, setSettings] = useLocalStorageState<ModelSettings>(
    LS_SETTINGS,
    DEFAULT_SETTINGS,
  );
  const [promptDraft, setPromptDraft] = useLocalStorageState<PromptDraftStored>(
    LS_PROMPT,
    DEFAULT_PROMPT,
  );
  const [chatHistory, setChatHistory] = useLocalStorageState<ChatMsg[]>(
    LS_CHAT,
    [],
  );
  const [versions, setVersions] = useLocalStorageState<PromptVersion[]>(
    LS_VERSIONS,
    [],
  );
  const [snippets, setSnippets] = useLocalStorageState<string[]>(LS_SNIPPETS, []);
  const [promptPreviewMode, setPromptPreviewMode] = useLocalStorageState<
    "concat" | "langsmith" | "openrouter"
  >(LS_PROMPT_PREVIEW_MODE, "concat");
  const [promptBuildMode, setPromptBuildMode] = useLocalStorageState<
    "single" | "multi"
  >(LS_PROMPT_BUILD_MODE, "single");
  const [lastAutoSavedAt, setLastAutoSavedAt] = useState<number | null>(null);

  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const prevApiKeyRef = useRef<string>("");
  const [userInput, setUserInput] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [showPayload, setShowPayload] = useState(false);
  const [lastRequest, setLastRequest] =
    useState<OpenRouterChatCompletionRequest | null>(null);
  const [lastResponse, setLastResponse] = useState<unknown>(null);
  const [lastHeaders, setLastHeaders] = useState<Record<string, string> | null>(
    null,
  );
  const [lastLangsmithPreview, setLastLangsmithPreview] = useState<string>("");

  const [editingMsg, setEditingMsg] = useState<
    | null
    | { kind: "first"; text: string }
    | { kind: "history"; index: number; text: string }
  >(null);
  const [translations, setTranslations] = useState<Record<number, string>>({});
  const [translatingIdx, setTranslatingIdx] = useState<number | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [diffTarget, setDiffTarget] = useState<PromptVersion | null>(null);
  const importInputRef = useRef<HTMLInputElement | null>(null);
  const importConversationInputRef = useRef<HTMLInputElement | null>(null);

  // 用户AI相关状态
  const [userAiPrompt, setUserAiPrompt] = useLocalStorageState<string>(
    LS_USER_AI_PROMPT,
    "你现在扮演一个用户，正在与AI角色对话。请根据对话上下文，站在用户的角度生成一条自然、合理的回复。只输出用户的回复内容，不要添加任何解释或前缀。"
  );
  const [userAiSending, setUserAiSending] = useState(false);

  const selectedModel = useMemo(
    () => models.find((m) => m.id === modelId) ?? null,
    [models, modelId],
  );

  // 迁移旧 localStorage（system/persona）到 systemBlocks，并修正版本里的 prompt 结构
  useEffect(() => {
    const coerced = coercePromptDraft(promptDraft as any);
    const same =
      JSON.stringify(coerced.systemBlocks) ===
        JSON.stringify((promptDraft as any).systemBlocks) &&
      coerced.variablesJson === (promptDraft as any).variablesJson;
    if (!same) setPromptDraft(coerced);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const next = versions.map((v) => ({
      ...v,
      prompt: coercePromptDraft((v as any).prompt),
    }));
    if (JSON.stringify(next) !== JSON.stringify(versions)) setVersions(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 启动时：从统一 ProjectState 恢复（若存在）
  useEffect(() => {
    try {
      const raw = localStorage.getItem(LS_PROJECT_STATE);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Partial<ProjectStateV1>;
      if (parsed.schema !== "mychatplayground.projectState.v1") return;

      if (typeof parsed.modelId === "string") setModelId(parsed.modelId);
      if (parsed.settings) setSettings(parsed.settings as ModelSettings);
      if (parsed.promptDraft) setPromptDraft(coercePromptDraft(parsed.promptDraft));
      if (Array.isArray(parsed.promptVersions)) {
        setVersions(
          (parsed.promptVersions as any[]).map((v) => ({
            ...v,
            prompt: coercePromptDraft((v as any).prompt),
          })),
        );
      }
      if (Array.isArray(parsed.chatHistory)) setChatHistory(parsed.chatHistory as ChatMsg[]);
      if (Array.isArray(parsed.snippets)) setSnippets(parsed.snippets as string[]);
      if (
        parsed.promptPreviewMode === "concat" ||
        parsed.promptPreviewMode === "langsmith" ||
        parsed.promptPreviewMode === "openrouter"
      ) {
        setPromptPreviewMode(parsed.promptPreviewMode);
      }
      if (typeof parsed.savedAt === "number") setLastAutoSavedAt(parsed.savedAt);
    } catch {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 实时自动保存：相关数据变更后防抖写入 ProjectState
  const autosaveTimerRef = useRef<number | null>(null);
  useEffect(() => {
    if (autosaveTimerRef.current) {
      window.clearTimeout(autosaveTimerRef.current);
    }
    autosaveTimerRef.current = window.setTimeout(() => {
      try {
        const state: ProjectStateV1 = {
          schema: "mychatplayground.projectState.v1",
          savedAt: Date.now(),
          modelId,
          settings,
          promptDraft: coercePromptDraft(promptDraft as any),
          promptVersions: versions.map((v) => ({
            ...v,
            prompt: coercePromptDraft((v as any).prompt),
          })),
          chatHistory,
          snippets,
          promptPreviewMode,
        };
        localStorage.setItem(LS_PROJECT_STATE, JSON.stringify(state));
        setLastAutoSavedAt(state.savedAt);
      } catch {
        // ignore
      }
    }, 300);

    return () => {
      if (autosaveTimerRef.current) {
        window.clearTimeout(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    modelId,
    settings,
    promptDraft,
    versions,
    chatHistory,
    snippets,
    promptPreviewMode,
  ]);

  const loadModels = async () => {
    setModelsLoading(true);
    setModelsError(null);
    try {
      const data = await fetchOpenRouterModels(apiKey || undefined);
      setModels(data);
      if (!modelId && data.length > 0) setModelId(data[0]!.id);
    } catch (e) {
      setModelsError(e instanceof Error ? e.message : String(e));
    } finally {
      setModelsLoading(false);
    }
  };

  // 避免首屏在未配置 key 时就报错；当用户首次填入 key 后自动拉取一次模型列表。
  useEffect(() => {
    const prev = prevApiKeyRef.current;
    prevApiKeyRef.current = apiKey;
    if (!prev && apiKey) {
      void loadModels();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey]);

  const varsParsed = useMemo(
    () => safeParseVars(promptDraft.variablesJson),
    [promptDraft.variablesJson],
  );

  const firstMessageText = useMemo(() => {
    if (!varsParsed.ok) return "";
    return buildFirstMessage({
      systemBlocks: promptDraft.systemBlocks,
      variables: varsParsed.value,
    });
  }, [promptDraft.systemBlocks, varsParsed]);

  const introText = useMemo(() => {
    if (!varsParsed.ok) return "";
    return buildIntroMessage({
      systemBlocks: promptDraft.systemBlocks,
      variables: varsParsed.value,
    });
  }, [promptDraft.systemBlocks, varsParsed]);

  const charDisplayName = useMemo(() => {
    if (!varsParsed.ok) return "AI";
    const c = String(varsParsed.value.char ?? "").trim();
    return c || "AI";
  }, [varsParsed]);

  const estimatedContextUsage = useMemo(() => {
    const vars = varsParsed.ok ? varsParsed.value : {};
    const systemText = (promptDraft.systemBlocks ?? [])
      .filter((b) => b.enabled !== false)
      .map((b) => b.content ?? "")
      .join("\n\n");
    const historyText = chatHistory
      .map((m) => `${m.role.toUpperCase()}:${m.content}`)
      .join("\n\n");
    const all = [systemText, firstMessageText, historyText]
      .filter(Boolean)
      .join("\n\n");
    const est = estimateTokensFromText(all);
    const ctx = selectedModel?.context_length;
    return { estTokens: est, contextLength: ctx ?? null };
  }, [
    chatHistory,
    firstMessageText,
    promptDraft.systemBlocks,
    selectedModel?.context_length,
    varsParsed,
  ]);

  const lastPromptPreview = useMemo(() => {
    if (!lastRequest?.messages?.length) return "";
    return lastRequest.messages
      .map((m) => `【${m.role.toUpperCase()}】\n${m.content}`)
      .join("\n\n---\n\n");
  }, [lastRequest]);

  const lastPromptPreviewForPanel = useMemo(() => {
    if (promptPreviewMode === "langsmith") return lastLangsmithPreview;
    if (promptPreviewMode === "openrouter") {
      if (!lastRequest) return "";
      return JSON.stringify(
        {
          url: "https://openrouter.ai/api/v1/chat/completions",
          headers: lastHeaders,
          body: lastRequest,
        },
        null,
        2,
      );
    }
    return lastPromptPreview;
  }, [lastHeaders, lastLangsmithPreview, lastPromptPreview, lastRequest, promptPreviewMode]);

  const lastPromptTokenCount = useMemo(() => {
    if (!lastRequest?.messages?.length) return 0;
    const allText = lastRequest.messages.map((m) => m.content).join("\n");
    return estimateTokensFromText(allText);
  }, [lastRequest]);

  function yamlNameScalar(name: string) {
    const s = name.trim();
    if (!s) return "Unknown";
    // 保守一点：有特殊字符就用 JSON 字符串作为 YAML 标量
    if (/[\n\r:#\[\]\{\},&*?]|^\s*-\s/.test(s)) return JSON.stringify(s);
    return s;
  }

  function yamlBlock(text: string, indent: number) {
    const pad = " ".repeat(indent);
    // 保留原始换行；空内容也要有一个空行以匹配示例观感
    const lines = (text ?? "").split("\n");
    return lines.map((l) => `${pad}${l}`).join("\n");
  }

  function toLangsmithYaml(args: {
    systemBlocks: PromptBlock[];
    firstMessage: string;
    userName: string;
    charName: string;
    chatHistory: ChatMsg[];
    newUserInput: string;
  }) {
    const { systemBlocks, firstMessage, userName, charName, chatHistory, newUserInput } =
      args;
    const items: Array<{ role: "system" | "user" | "assistant"; content: string; name?: string }> =
      [];

    for (const b of systemBlocks) {
      if (b.enabled === false) continue;
      if (b.id === "block-first-message") continue;
      const c = (b.content ?? "").trim();
      if (!c) continue;
      items.push({ role: "system", content: c });
    }

    if (firstMessage.trim()) {
      items.push({ role: "assistant", name: charName, content: firstMessage.trim() });
    }

    for (const m of chatHistory) {
      items.push({
        role: m.role,
        name: m.role === "user" ? userName : charName,
        content: m.content,
      });
    }

    items.push({ role: "user", name: userName, content: newUserInput });

    // 按你给的示例格式输出：messages: + list，system 无 name，user/assistant 有 name；content 用 |-。
    const out: string[] = [];
    out.push("messages:");
    for (const it of items) {
      out.push(`  - content: |-`);
      out.push(yamlBlock(it.content ?? "", 6));
      if (it.role !== "system") out.push(`    name: ${yamlNameScalar(it.name ?? "")}`);
      out.push(`    role: ${it.role}`);
    }
    return out.join("\n");
  }

  const resetChat = () => {
    setChatHistory([]);
    setChatError(null);
  };

  const updateFirstMessageBlock = (nextContent: string) => {
    const nextBlocks = [...promptDraft.systemBlocks];
    const idx = nextBlocks.findIndex((b) => b.id === "block-first-message");
    if (idx < 0) return;
    nextBlocks[idx] = { ...nextBlocks[idx]!, content: nextContent };
    setPromptDraft({ ...promptDraft, systemBlocks: nextBlocks });
  };

  const startEditHistory = (index: number) => {
    const msg = chatHistory[index];
    if (!msg) return;
    setEditingMsg({ kind: "history", index, text: msg.content });
  };

  const saveEdit = () => {
    if (!editingMsg) return;
    if (editingMsg.kind === "first") {
      updateFirstMessageBlock(editingMsg.text);
      setEditingMsg(null);
      return;
    }
    const idx = editingMsg.index;
    const next = [...chatHistory];
    if (!next[idx]) return;
    next[idx] = { ...next[idx]!, content: editingMsg.text };
    setChatHistory(next);
    setEditingMsg(null);
  };

  const cancelEdit = () => setEditingMsg(null);

  const retractFromUserMessage = (index: number) => {
    const msg = chatHistory[index];
    if (!msg || msg.role !== "user") return;
    const ok = window.confirm("撤回这条用户消息，并删除其后的所有聊天记录？");
    if (!ok) return;

    setChatHistory(chatHistory.slice(0, index));
    setChatError(null);

    // 清理调试/预览缓存，避免展示已不存在的请求
    setLastRequest(null);
    setLastResponse(null);
    setLastHeaders(null);
    setLastLangsmithPreview("");

    // 若当前在编辑被删的消息，退出编辑态
    if (editingMsg?.kind === "history" && editingMsg.index >= index) {
      setEditingMsg(null);
    }
  };

  const deleteMessage = (index: number) => {
    const msg = chatHistory[index];
    if (!msg) return;
    
    const next = chatHistory.filter((_, i) => i !== index);
    setChatHistory(next);
    
    // 清除该消息的翻译（如果有）
    if (translations[index]) {
      const newTranslations = { ...translations };
      delete newTranslations[index];
      // 调整后续索引的翻译
      const adjusted: Record<number, string> = {};
      for (const [key, value] of Object.entries(newTranslations)) {
        const numKey = Number(key);
        if (numKey > index) {
          adjusted[numKey - 1] = value;
        } else {
          adjusted[numKey] = value;
        }
      }
      setTranslations(adjusted);
    }
    
    // 若当前在编辑被删的消息，退出编辑态
    if (editingMsg?.kind === "history" && editingMsg.index === index) {
      setEditingMsg(null);
    }
    // 调整编辑索引（如果在删除位置之后）
    if (editingMsg?.kind === "history" && editingMsg.index > index) {
      setEditingMsg({ ...editingMsg, index: editingMsg.index - 1 });
    }
  };

  const addSnippet = (text: string) => {
    const t = text.trim();
    if (!t) return;
    if (snippets.includes(t)) return;
    setSnippets([t, ...snippets]);
  };

  const applySnippetToBlock = (blockId: string, text: string) => {
    const next = [...promptDraft.systemBlocks];
    const idx = next.findIndex((b) => b.id === blockId);
    if (idx < 0) return;
    next[idx] = { ...next[idx]!, content: text };
    setPromptDraft({ ...promptDraft, systemBlocks: next });
  };

  const saveVersion = () => {
    const name = window.prompt("版本名：", `v${versions.length + 1}`)?.trim();
    if (!name) return;
    const v: PromptVersion = {
      id: crypto.randomUUID(),
      name,
      createdAt: Date.now(),
      prompt: coercePromptDraft(promptDraft as any),
    };
    setVersions([v, ...versions]);
  };

  const applyVersion = (v: PromptVersion) => {
    setPromptDraft(v.prompt);
  };

  const deleteVersion = (v: PromptVersion) => {
    if (!window.confirm(`删除版本「${v.name}」？`)) return;
    setVersions(versions.filter((x) => x.id !== v.id));
  };

  const openDiff = (v: PromptVersion) => {
    setDiffTarget(v);
    setShowDiff(true);
  };

  /**
   * 检测文本是否包含英文字母（至少有连续英文单词）
   */
  const hasEnglish = (text: string) => {
    // 至少包含一个英文单词（2个以上连续字母）
    return /[a-zA-Z]{2,}/.test(text);
  };

  /**
   * 翻译 AI 消息（英文 -> 中文）
   */
  const translateMessage = async (idx: number, content: string) => {
    if (!hasEnglish(content)) {
      return; // 没有英文，不翻译
    }
    if (!apiKey.trim()) {
      setChatError("请先填写 OpenRouter API Key");
      return;
    }
    if (!modelId) {
      setChatError("请先选择模型");
      return;
    }

    setTranslatingIdx(idx);
    try {
      const resp = await createOpenRouterChatCompletion({
        apiKey: apiKey.trim(),
        request: {
          model: modelId,
          messages: [
            {
              role: "system",
              content: "你是一个翻译助手。请将用户提供的英文文本翻译成中文。只输出翻译结果，不要添加任何解释或额外内容。如果文本中有中文部分，保留原样。",
            },
            {
              role: "user",
              content: content,
            },
          ],
          temperature: 0.3,
          max_tokens: 2000,
        },
        siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground",
      });
      const respContent = resp.choices?.[0]?.message?.content;
      const translated = typeof respContent === "string" ? respContent.trim() : "";
      if (translated) {
        setTranslations((prev) => ({ ...prev, [idx]: translated }));
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setChatError(`翻译失败：${msg}`);
    } finally {
      setTranslatingIdx(null);
    }
  };

  const exportJson = () => {
    const bundle: ExportBundleV3 = {
      schema: "mychatplayground.export.v3",
      exportedAt: Date.now(),
      modelId,
      settings,
      promptDraft: coercePromptDraft(promptDraft as any),
      promptVersions: versions.map((v) => ({ ...v, prompt: coercePromptDraft((v as any).prompt) })),
      chatHistory,
    };
    const text = JSON.stringify(bundle, null, 2);
    const blob = new Blob([text], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mychatplayground-export-${new Date()
      .toISOString()
      .slice(0, 19)
      .replace(/[:T]/g, "-")}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const triggerImport = () => {
    importInputRef.current?.click();
  };

  const importJson = async (file: File) => {
    const text = await file.text();
    const parsed = JSON.parse(text) as Partial<
      ExportBundleV1 | ExportBundleV2 | ExportBundleV3
    >;
    if (parsed.schema === "mychatplayground.export.v3") {
      if ((parsed as any).promptDraft)
        setPromptDraft(coercePromptDraft((parsed as any).promptDraft));
      if ((parsed as any).promptVersions) {
        setVersions(
          ((parsed as any).promptVersions as any[]).map((v) => ({
            ...v,
            prompt: coercePromptDraft((v as any).prompt),
          })),
        );
      }
      if ((parsed as any).chatHistory) setChatHistory((parsed as any).chatHistory);
      if ((parsed as any).settings) setSettings((parsed as any).settings);
      if (typeof (parsed as any).modelId === "string")
        setModelId((parsed as any).modelId);
      return;
    }
    if (parsed.schema === "mychatplayground.export.v2") {
      if ((parsed as any).promptDraft) setPromptDraft(coercePromptDraft((parsed as any).promptDraft));
      if ((parsed as any).promptVersions) {
        setVersions(
          ((parsed as any).promptVersions as any[]).map((v) => ({
            ...v,
            prompt: coercePromptDraft((v as any).prompt),
          })),
        );
      }
      if ((parsed as any).chatHistory) setChatHistory((parsed as any).chatHistory);
      if ((parsed as any).settings) setSettings((parsed as any).settings);
      if (typeof (parsed as any).modelId === "string") setModelId((parsed as any).modelId);
      return;
    }
    if (parsed.schema === "mychatplayground.export.v1") {
      if ((parsed as any).promptDraft) setPromptDraft(coercePromptDraft((parsed as any).promptDraft));
      if ((parsed as any).promptVersions) {
        setVersions(
          ((parsed as any).promptVersions as any[]).map((v) => ({
            ...v,
            prompt: coercePromptDraft((v as any).prompt),
          })),
        );
      }
      if ((parsed as any).chatHistory) setChatHistory((parsed as any).chatHistory);
      if ((parsed as any).settings) setSettings((parsed as any).settings);
      if (typeof (parsed as any).modelId === "string") setModelId((parsed as any).modelId);
      return;
    }
    throw new Error("不支持的导入格式（schema 不匹配）");
  };

  const triggerImportConversation = () => {
    importConversationInputRef.current?.click();
  };

  const importConversationLog = async (file: File) => {
    const text = await file.text();
    const { messages, info } = parseConversationLog(text);
    
    if (messages.length === 0) {
      throw new Error("未能从文件中解析出任何对话消息");
    }
    
    // 将导入的消息追加到现有聊天历史（或替换，取决于用户选择）
    const shouldReplace = window.confirm(
      `${info}\n\n是否替换现有聊天记录？\n- 确定：替换现有记录\n- 取消：追加到现有记录`
    );
    
    if (shouldReplace) {
      setChatHistory(messages);
    } else {
      setChatHistory([...chatHistory, ...messages]);
    }
    
    window.alert(info);
  };

  /**
   * 用户AI：让AI模拟用户视角生成一条消息
   */
  const generateUserAiMessage = async () => {
    if (!apiKey.trim()) {
      setChatError("请先填写 OpenRouter API Key");
      return;
    }
    if (!modelId) {
      setChatError("请先选择模型");
      return;
    }
    if (!userAiPrompt.trim()) {
      setChatError("请先填写用户AI提示词");
      return;
    }

    setUserAiSending(true);
    setChatError(null);

    try {
      // 构建用户AI的消息上下文
      const contextMessages: Array<{ role: "system" | "user" | "assistant"; content: string }> = [];
      
      // 用户AI的系统提示词
      contextMessages.push({
        role: "system",
        content: userAiPrompt.trim(),
      });

      // 添加角色设定的简要信息（让用户AI了解对话背景）
      const charName = varsParsed.ok ? (varsParsed.value.char || "AI角色") : "AI角色";
      const userName = varsParsed.ok ? (varsParsed.value.user || "用户") : "用户";
      
      // 添加场景介绍（如果有）
      if (introText) {
        contextMessages.push({
          role: "system",
          content: `【场景背景】\n${introText}`,
        });
      }

      // 添加对话历史（调换角色视角：原来的 user 变成 assistant，原来的 assistant 变成 user）
      // 因为用户AI需要站在用户的角度，所以它看到的"对方"是 AI角色
      if (firstMessageText) {
        contextMessages.push({
          role: "user",
          content: `[${charName}]: ${firstMessageText}`,
        });
      }

      for (const msg of chatHistory) {
        if (msg.role === "user") {
          // 原来用户说的话，对于用户AI来说是"自己之前说的"
          contextMessages.push({
            role: "assistant",
            content: `[${userName}]: ${msg.content}`,
          });
        } else {
          // 原来AI角色说的话，对于用户AI来说是"对方说的"
          contextMessages.push({
            role: "user",
            content: `[${charName}]: ${msg.content}`,
          });
        }
      }

      // 请求用户AI生成回复
      const resp = await createOpenRouterChatCompletion({
        apiKey: apiKey.trim(),
        request: {
          model: modelId,
          messages: contextMessages,
          temperature: settings.temperature,
          max_tokens: settings.max_tokens,
        },
        siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground",
      });

      const generatedContent = resp.choices?.[0]?.message?.content;
      const userMessage = typeof generatedContent === "string" 
        ? generatedContent.trim().replace(/^\[.*?\]:\s*/, "") // 移除可能的前缀如 "[用户]: "
        : "";

      if (userMessage) {
        // 将生成的消息作为用户输入发送
        await sendMessage(userMessage);
      } else {
        setChatError("用户AI未能生成有效回复");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setChatError(`用户AI生成失败：${msg}`);
    } finally {
      setUserAiSending(false);
    }
  };

  const sendMessage = async (overrideInput?: string) => {
    const input = (overrideInput ?? userInput).trim();
    if (!input) return;
    if (!apiKey.trim()) {
      setChatError("请先填写 OpenRouter API Key");
      return;
    }
    if (!modelId) {
      setChatError("请先选择模型");
      return;
    }
    if (!varsParsed.ok) {
      setChatError(`变量 JSON 无法解析：${varsParsed.error}`);
      return;
    }

    setSending(true);
    setChatError(null);
    setUserInput("");

    const historyBefore = chatHistory;
    setChatHistory([...historyBefore, { role: "user", content: input }]);

    const userName = (varsParsed.value.user || "").trim() || undefined;
    const charName = (varsParsed.value.char || "").trim() || undefined;

    const messages = promptBuildMode === "multi"
      ? buildMessagesMultiSystem({
          prompt: {
            systemBlocks: promptDraft.systemBlocks,
            variables: varsParsed.value,
          },
          chatHistory: historyBefore,
          newUserInput: input,
          userName,
          charName,
        })
      : buildMessages({
          prompt: {
            systemBlocks: promptDraft.systemBlocks,
            variables: varsParsed.value,
          },
          chatHistory: historyBefore,
          newUserInput: input,
        });

    const req: OpenRouterChatCompletionRequest = {
      model: modelId,
      messages,
      temperature: settings.temperature,
      top_p: settings.top_p,
      max_tokens: settings.max_tokens,
      presence_penalty: settings.presence_penalty,
      frequency_penalty: settings.frequency_penalty,
    };
    setLastRequest(req);
    setLastResponse(null);
    setLastHeaders({
      Authorization: `Bearer ${apiKey.trim().slice(0, 6)}...（已脱敏）`,
      "Content-Type": "application/json",
      "HTTP-Referer":
        typeof window !== "undefined" ? window.location.origin : "(unknown)",
      "X-Title": "mychatplayground",
    });

    // 生成"LangSmith 多 system"预览（严格按示例 YAML messages 格式）
    setLastLangsmithPreview(
      toLangsmithYaml({
        systemBlocks: promptDraft.systemBlocks,
        firstMessage: firstMessageText,
        userName: userName || "User",
        charName: charName || "Char",
        chatHistory: historyBefore,
        newUserInput: input,
      }),
    );

    try {
      const resp = await createOpenRouterChatCompletion({
        apiKey: apiKey.trim(),
        request: req,
        siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground",
      });
      setLastResponse(resp);
      const messageContent = resp.choices?.[0]?.message?.content;
      const assistantContent =
        typeof messageContent === "string" ? messageContent.trim() : "(空响应/无 choices)";
      setChatHistory([
        ...historyBefore,
        { role: "user", content: input },
        { role: "assistant", content: assistantContent },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setChatError(msg);
      setLastResponse({ error: msg });
      // 保留用户输入已入历史，便于重试
      setChatHistory([...historyBefore, { role: "user", content: input }]);
    } finally {
      setSending(false);
    }
  };

  const retryLastAi = async () => {
    if (sending) return;
    if (!apiKey.trim()) {
      setChatError("请先填写 OpenRouter API Key");
      return;
    }
    if (!modelId) {
      setChatError("请先选择模型");
      return;
    }
    if (!varsParsed.ok) {
      setChatError(`变量 JSON 无法解析：${varsParsed.error}`);
      return;
    }

    // 仅支持：最后一条是 assistant，并且它前面能找到 user
    const lastIdx = chatHistory.length - 1;
    if (lastIdx < 0 || chatHistory[lastIdx]?.role !== "assistant") {
      setChatError("当前没有可重试的 AI 回复（需要最后一条为角色消息）");
      return;
    }
    let lastUserIdx = -1;
    for (let i = lastIdx - 1; i >= 0; i--) {
      if (chatHistory[i]?.role === "user") {
        lastUserIdx = i;
        break;
      }
    }
    if (lastUserIdx < 0) {
      setChatError("找不到上一条用户输入，无法重试");
      return;
    }

    const input = chatHistory[lastUserIdx]!.content;
    const historyBefore = chatHistory.slice(0, lastUserIdx);

    setSending(true);
    setChatError(null);

    // 保留用户输入，移除旧 AI 回复（稍后用新回复覆盖）
    setChatHistory([...historyBefore, { role: "user", content: input }]);

    const userName = (varsParsed.value.user || "").trim() || undefined;
    const charName = (varsParsed.value.char || "").trim() || undefined;

    const messages = promptBuildMode === "multi"
      ? buildMessagesMultiSystem({
          prompt: {
            systemBlocks: promptDraft.systemBlocks,
            variables: varsParsed.value,
          },
          chatHistory: historyBefore,
          newUserInput: input,
          userName,
          charName,
        })
      : buildMessages({
          prompt: {
            systemBlocks: promptDraft.systemBlocks,
            variables: varsParsed.value,
          },
          chatHistory: historyBefore,
          newUserInput: input,
        });

    const req: OpenRouterChatCompletionRequest = {
      model: modelId,
      messages,
      temperature: settings.temperature,
      top_p: settings.top_p,
      max_tokens: settings.max_tokens,
      presence_penalty: settings.presence_penalty,
      frequency_penalty: settings.frequency_penalty,
    };

    setLastRequest(req);
    setLastResponse(null);
    setLastHeaders({
      Authorization: `Bearer ${apiKey.trim().slice(0, 6)}...（已脱敏）`,
      "Content-Type": "application/json",
      "HTTP-Referer":
        typeof window !== "undefined" ? window.location.origin : "(unknown)",
      "X-Title": "mychatplayground",
    });

    setLastLangsmithPreview(
      toLangsmithYaml({
        systemBlocks: promptDraft.systemBlocks,
        firstMessage: firstMessageText,
        userName: userName || "User",
        charName: charName || "Char",
        chatHistory: historyBefore,
        newUserInput: input,
      }),
    );

    try {
      const resp = await createOpenRouterChatCompletion({
        apiKey: apiKey.trim(),
        request: req,
        siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground",
      });
      setLastResponse(resp);
      const retryMessageContent = resp.choices?.[0]?.message?.content;
      const retryAssistantContent =
        typeof retryMessageContent === "string" ? retryMessageContent.trim() : "(空响应/无 choices)";
      setChatHistory([
        ...historyBefore,
        { role: "user", content: input },
        { role: "assistant", content: retryAssistantContent },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setChatError(msg);
      setLastResponse({ error: msg });
      setChatHistory([...historyBefore, { role: "user", content: input }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="h-full w-full bg-zinc-50 text-zinc-950">
      <div className="flex h-full w-full flex-col">
        <div className="grid h-full grid-cols-12 gap-0">
          <section className="col-span-5 h-full overflow-auto border-r border-zinc-200 bg-white p-4">
            <div className="space-y-6">
              {/* 工具栏 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm hover:bg-zinc-50"
                    onClick={() => setShowPayload(true)}
                  >
                    查看 Payload
                  </button>
                  <button
                    type="button"
                    className="rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm hover:bg-zinc-50"
                    onClick={loadModels}
                    disabled={modelsLoading}
                  >
                    {modelsLoading ? "加载中..." : "刷新模型列表"}
                  </button>
                </div>
                {lastAutoSavedAt ? (
                  <div className="text-xs text-zinc-400">
                    自动保存：{new Date(lastAutoSavedAt).toLocaleTimeString()}
                  </div>
                ) : null}
              </div>

              <div>
                <div className="mb-2 text-sm font-medium">OpenRouter API Key</div>
                <input
                  className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  placeholder="粘贴你的 OpenRouter Key（仅保存在本地）"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
                <div className="mt-2 text-xs text-zinc-500">
                  说明：Key 仅存于浏览器 localStorage；导出 JSON 时不会包含。
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-sm font-medium">模型</div>
                  <div className="text-xs text-zinc-500">
                    {selectedModel?.context_length
                      ? `context: ${selectedModel.context_length}`
                      : null}
                  </div>
                </div>
                <select
                  className="w-full rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  disabled={models.length === 0}
                >
                  {models.length === 0 ? (
                    <option value="">
                      {apiKey
                        ? "（未加载模型列表，点右上角“刷新模型列表”）"
                        : "（先填写 API Key）"}
                    </option>
                  ) : null}
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id}
                    </option>
                  ))}
                </select>
                {modelsError ? (
                  <div className="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                    {modelsError}
                  </div>
                ) : null}
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-800"
                  onClick={saveVersion}
                >
                  保存版本
                </button>
                <button
                  type="button"
                  className="rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm hover:bg-zinc-50"
                  onClick={exportJson}
                >
                  导出 JSON
                </button>
                <button
                  type="button"
                  className="rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm hover:bg-zinc-50"
                  onClick={triggerImport}
                >
                  导入 JSON
                </button>
                <input
                  ref={importInputRef}
                  type="file"
                  accept="application/json"
                  className="hidden"
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    try {
                      await importJson(f);
                    } catch (err) {
                      const msg =
                        err instanceof Error ? err.message : String(err);
                      window.alert(`导入失败：${msg}`);
                    } finally {
                      // allow re-import same file
                      e.target.value = "";
                    }
                  }}
                />
                <button
                  type="button"
                  className="rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm text-amber-800 hover:bg-amber-100"
                  onClick={triggerImportConversation}
                  title="导入对话记录 txt 文件（支持会话导出格式）"
                >
                  导入对话记录
                </button>
                <input
                  ref={importConversationInputRef}
                  type="file"
                  accept=".txt"
                  className="hidden"
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    try {
                      await importConversationLog(f);
                    } catch (err) {
                      const msg =
                        err instanceof Error ? err.message : String(err);
                      window.alert(`导入对话记录失败：${msg}`);
                    } finally {
                      // allow re-import same file
                      e.target.value = "";
                    }
                  }}
                />
              </div>

              <div className="flex items-end gap-2 overflow-x-auto">
                <label className="shrink-0 space-y-0.5">
                  <div className="text-[11px] font-medium text-zinc-700">
                    temperature
                  </div>
                  <input
                    type="number"
                    step="0.1"
                    className="w-28 rounded-md border border-zinc-200 px-2 py-1.5 text-right text-xs tabular-nums outline-none focus:border-zinc-400"
                    value={settings.temperature}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        temperature: Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label className="shrink-0 space-y-0.5">
                  <div className="text-[11px] font-medium text-zinc-700">top_p</div>
                  <input
                    type="number"
                    step="0.05"
                    className="w-28 rounded-md border border-zinc-200 px-2 py-1.5 text-right text-xs tabular-nums outline-none focus:border-zinc-400"
                    value={settings.top_p}
                    onChange={(e) =>
                      setSettings({ ...settings, top_p: Number(e.target.value) })
                    }
                  />
                </label>
                <label className="shrink-0 space-y-0.5">
                  <div className="text-[11px] font-medium text-zinc-700">
                    max_tokens
                  </div>
                  <input
                    type="number"
                    step="1"
                    className="w-32 rounded-md border border-zinc-200 px-2 py-1.5 text-right text-xs tabular-nums outline-none focus:border-zinc-400"
                    value={settings.max_tokens}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        max_tokens: Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label className="shrink-0 space-y-0.5">
                  <div className="text-[11px] font-medium text-zinc-700">
                    presence_penalty
                  </div>
                  <input
                    type="number"
                    step="0.1"
                    className="w-28 rounded-md border border-zinc-200 px-2 py-1.5 text-right text-xs tabular-nums outline-none focus:border-zinc-400"
                    value={settings.presence_penalty}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        presence_penalty: Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label className="shrink-0 space-y-0.5">
                  <div className="text-[11px] font-medium text-zinc-700">
                    frequency_penalty
                  </div>
                  <input
                    type="number"
                    step="0.1"
                    className="w-28 rounded-md border border-zinc-200 px-2 py-1.5 text-right text-xs tabular-nums outline-none focus:border-zinc-400"
                    value={settings.frequency_penalty}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        frequency_penalty: Number(e.target.value),
                      })
                    }
                  />
                </label>
              </div>

              <div className="flex items-center justify-between">
                <div className="text-sm font-medium">提示词（初始）</div>
                <div className="flex items-center gap-2">
                  <select
                    className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs"
                    onChange={(e) => {
                      const t = PROMPT_TEMPLATES.find(
                        (x) => x.name === e.target.value,
                      );
                      if (t) setPromptDraft(t.value);
                    }}
                    defaultValue={PROMPT_TEMPLATES[0]?.name ?? ""}
                  >
                    {PROMPT_TEMPLATES.map((t) => (
                      <option key={t.name} value={t.name}>
                        模板：{t.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="text-sm font-medium">System Prompt Blocks</div>
                    <select
                      className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs"
                      value={promptBuildMode}
                      onChange={(e) =>
                        setPromptBuildMode(e.target.value as "single" | "multi")
                      }
                      title="选择 system 拼接方式"
                    >
                      <option value="single">单 system（合并）</option>
                      <option value="multi">多 system（LangSmith）</option>
                    </select>
                  </div>
                  <button
                    type="button"
                    className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
                    onClick={() => {
                      const next: PromptBlock = {
                        id: crypto.randomUUID(),
                        title: `Block ${promptDraft.systemBlocks.length + 1}`,
                        enabled: true,
                        content: "",
                      };
                      setPromptDraft({
                        ...promptDraft,
                        systemBlocks: [...promptDraft.systemBlocks, next],
                      });
                    }}
                  >
                    + 新增 block
                  </button>
                </div>

                <div className="space-y-2">
                  {promptDraft.systemBlocks.map((b, idx) => (
                    <div
                      key={b.id}
                      className="rounded-md border border-zinc-200 bg-white p-3"
                    >
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <div className="flex min-w-0 items-center gap-2">
                          <input
                            type="checkbox"
                            checked={b.enabled !== false}
                            onChange={(e) => {
                              const next = [...promptDraft.systemBlocks];
                              next[idx] = { ...b, enabled: e.target.checked };
                              setPromptDraft({ ...promptDraft, systemBlocks: next });
                            }}
                          />
                          <input
                            className="w-40 rounded-md border border-zinc-200 px-2 py-1 text-xs outline-none focus:border-zinc-400"
                            value={b.title}
                            onChange={(e) => {
                              const next = [...promptDraft.systemBlocks];
                              next[idx] = { ...b, title: e.target.value };
                              setPromptDraft({ ...promptDraft, systemBlocks: next });
                            }}
                          />
                          <div className="text-xs text-zinc-500">#{idx + 1}</div>
                        </div>
                        <div className="flex items-center gap-1">
                          <details className="relative">
                            <summary className="list-none">
                              <span className="inline-flex cursor-pointer select-none items-center rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50">
                                片段
                              </span>
                            </summary>
                            <div className="absolute right-0 mt-1 w-72 overflow-hidden rounded-md border border-zinc-200 bg-white shadow-lg">
                              <div className="border-b border-zinc-200 px-3 py-2 text-xs font-medium text-zinc-700">
                                片段库（仅文本内容）
                              </div>
                              <div className="max-h-64 overflow-auto p-1">
                                <button
                                  type="button"
                                  className="w-full rounded-md px-2 py-2 text-left text-xs hover:bg-zinc-50"
                                  onClick={(e) => {
                                    addSnippet(b.content);
                                    (e.currentTarget.closest("details") as HTMLDetailsElement | null)?.removeAttribute(
                                      "open",
                                    );
                                  }}
                                  disabled={!b.content.trim()}
                                >
                                  保存当前内容到片段库
                                  {!b.content.trim() ? (
                                    <span className="ml-2 text-zinc-400">
                                      （当前为空）
                                    </span>
                                  ) : null}
                                </button>
                                <div className="my-1 border-t border-zinc-200" />
                                {snippets.length === 0 ? (
                                  <div className="px-2 py-2 text-xs text-zinc-500">
                                    暂无片段。先在任意 block 里写点内容，再点“保存当前内容到片段库”。
        </div>
                                ) : (
                                  snippets.map((s, sIdx) => (
                                    <button
                                      key={`${sIdx}-${s.slice(0, 16)}`}
                                      type="button"
                                      className="w-full rounded-md px-2 py-2 text-left text-xs hover:bg-zinc-50"
                                      onClick={(e) => {
                                        applySnippetToBlock(b.id, s);
                                        (e.currentTarget.closest("details") as HTMLDetailsElement | null)?.removeAttribute(
                                          "open",
                                        );
                                      }}
                                      title="点击填充到当前 block"
                                    >
                                      <div className="line-clamp-2 whitespace-pre-wrap text-zinc-800">
                                        {s.length > 120 ? `${s.slice(0, 120)}…` : s}
                                      </div>
                                    </button>
                                  ))
                                )}
                              </div>
                            </div>
                          </details>
                          <button
                            type="button"
                            className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50 disabled:opacity-50"
                            disabled={idx === 0}
                            onClick={() => {
                              if (idx === 0) return;
                              const next = [...promptDraft.systemBlocks];
                              const tmp = next[idx - 1]!;
                              next[idx - 1] = next[idx]!;
                              next[idx] = tmp;
                              setPromptDraft({ ...promptDraft, systemBlocks: next });
                            }}
                          >
                            上移
                          </button>
                          <button
                            type="button"
                            className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50 disabled:opacity-50"
                            disabled={idx === promptDraft.systemBlocks.length - 1}
                            onClick={() => {
                              if (idx === promptDraft.systemBlocks.length - 1) return;
                              const next = [...promptDraft.systemBlocks];
                              const tmp = next[idx + 1]!;
                              next[idx + 1] = next[idx]!;
                              next[idx] = tmp;
                              setPromptDraft({ ...promptDraft, systemBlocks: next });
                            }}
                          >
                            下移
                          </button>
                          <button
                            type="button"
                            className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs text-red-700 hover:bg-zinc-50"
                            onClick={() => {
                              const next = promptDraft.systemBlocks.filter((x) => x.id !== b.id);
                              setPromptDraft({
                                ...promptDraft,
                                systemBlocks: next.length ? next : makeDefaultSystemBlocks(),
                              });
                            }}
                          >
                            删除
                          </button>
                        </div>
                      </div>

                      <textarea
                        className="min-h-20 w-full resize-y rounded-md border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                        value={b.content}
                        onChange={(e) => {
                          const next = [...promptDraft.systemBlocks];
                          next[idx] = { ...b, content: e.target.value };
                          setPromptDraft({ ...promptDraft, systemBlocks: next });
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <label className="space-y-1">
                <div className="text-xs font-medium text-zinc-700">
                  变量（JSON 对象，支持 {"{{var}}"}）
                </div>
                <textarea
                  className="min-h-24 w-full resize-y rounded-md border border-zinc-200 px-3 py-2 font-mono text-xs outline-none focus:border-zinc-400"
                  value={promptDraft.variablesJson}
                  onChange={(e) =>
                    setPromptDraft({
                      ...promptDraft,
                      variablesJson: e.target.value,
                    })
                  }
                />
                {!varsParsed.ok ? (
                  <div className="space-y-2">
                    <div className="text-xs text-red-600">
                      JSON 解析错误：{varsParsed.error}
                    </div>
                    <div className="text-xs text-zinc-600">
                      常见原因：少了逗号。比如{" "}
                      <span className="font-mono">
                        {"\"user\": \"JOY\","}
                      </span>{" "}
                      这一行末尾需要逗号。
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
                        onClick={() =>
                          setPromptDraft({
                            ...promptDraft,
                            variablesJson: "{}",
                          })
                        }
                      >
                        修复：清空为 {"{}"}
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
                        onClick={() =>
                          setPromptDraft({
                            ...promptDraft,
                            variablesJson: DEFAULT_PROMPT.variablesJson,
                          })
                        }
                      >
                        修复：恢复默认变量（JOY/Oaklyn）
                      </button>
                    </div>
                  </div>
                ) : null}
              </label>

              {/* 用户AI提示词 */}
              <div className="space-y-2 rounded-md border border-indigo-200 bg-indigo-50/50 p-3">
                <div className="flex items-center gap-2">
                  <div className="text-sm font-medium text-indigo-900">用户AI 提示词</div>
                  <div className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] text-indigo-700">
                    模拟用户发言
                  </div>
                </div>
                <div className="text-xs text-indigo-700/80">
                  点击聊天框的「AI发送」按钮时，会用这个提示词让AI站在用户视角生成一条消息。
                </div>
                <textarea
                  className="min-h-20 w-full resize-y rounded-md border border-indigo-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-400"
                  placeholder="描述用户AI应该如何模拟用户发言..."
                  value={userAiPrompt}
                  onChange={(e) => setUserAiPrompt(e.target.value)}
                />
              </div>

              <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-700">
                估算上下文：约 {estimatedContextUsage.estTokens} tokens
                {estimatedContextUsage.contextLength
                  ? ` / ${estimatedContextUsage.contextLength}`
                  : ""}
                {estimatedContextUsage.contextLength &&
                estimatedContextUsage.estTokens >
                  estimatedContextUsage.contextLength * 0.8 ? (
                  <span className="ml-2 text-amber-700">
                    （接近上限，可能被截断）
                  </span>
                ) : null}
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">提示版本</div>
                {versions.length === 0 ? (
                  <div className="text-sm text-zinc-500">暂无保存版本。</div>
                ) : (
                  <div className="space-y-2">
                    {versions.map((v) => (
                      <div
                        key={v.id}
                        className="flex items-center justify-between rounded-md border border-zinc-200 px-3 py-2"
                      >
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium">
                            {v.name}
                          </div>
                          <div className="text-xs text-zinc-500">
                            {new Date(v.createdAt).toLocaleString()}
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <button
                            type="button"
                            className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
                            onClick={() => applyVersion(v)}
                          >
                            应用
                          </button>
                          <button
                            type="button"
                            className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
                            onClick={() => openDiff(v)}
                          >
                            Diff
                          </button>
                          <button
                            type="button"
                            className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs text-red-700 hover:bg-zinc-50"
                            onClick={() => deleteVersion(v)}
                          >
                            删除
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
        </div>
          </section>

          <section className="col-span-7 h-full overflow-auto bg-zinc-50 p-4">
            <div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-2">
              {/* Chat panel */}
              <div className="flex h-full min-h-0 flex-col items-center">
                <div className="relative flex h-full w-full max-w-[520px] flex-col overflow-hidden rounded-[2.5rem] border border-zinc-800 bg-zinc-900 shadow-[0_24px_60px_-24px_rgba(0,0,0,0.65)]">
                  {/* notch */}
                  <div className="pointer-events-none absolute left-1/2 top-3 h-6 w-36 -translate-x-1/2 rounded-full bg-zinc-800/80" />

                  {/* phone top bar */}
                  <div className="flex items-center justify-between gap-2 px-5 pt-5 pb-3 text-zinc-100">
                    <div className="flex items-center gap-2">
                      <div className="text-xs font-semibold">{charDisplayName}</div>
                      <div className="text-[11px] text-zinc-300">Chat</div>
                    </div>
                    <button
                      type="button"
                      className="rounded-xl bg-zinc-800/70 px-3 py-1.5 text-xs text-zinc-100 hover:bg-zinc-800 disabled:opacity-50"
                      onClick={resetChat}
                      disabled={sending || chatHistory.length === 0}
                    >
                      清空
                    </button>
                  </div>

                  {/* screen */}
                  <div className="mx-3 mb-3 min-h-0 flex-1 overflow-hidden rounded-[1.75rem] bg-zinc-50">
                    <div className="flex h-full min-h-0 flex-col">
                      <div className="min-h-0 flex-1 overflow-auto p-3">
                        {chatHistory.length === 0 && !firstMessageText && !introText ? (
                          <div className="text-sm text-zinc-500">
                            还没有消息。下方输入内容开始聊天。
                          </div>
                        ) : (
                          <div className="space-y-3">
                          {introText ? (
                            <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 px-4 py-3 shadow-sm">
                              <div className="mb-1 text-center text-xs font-medium text-amber-700">📖 场景</div>
                              <div className="whitespace-pre-wrap text-sm text-zinc-700">
                                {introText}
                              </div>
                            </div>
                          ) : null}
                          {firstMessageText ? (
                            <div className="flex justify-start">
                              <div
                                className={
                                  editingMsg?.kind === "first"
                                    ? "w-full max-w-[85%]"
                                    : "max-w-[85%]"
                                }
                              >
                                <div className="mb-1 flex items-center justify-between gap-2">
                                  <div className="text-xs font-medium text-zinc-600">
                                    {charDisplayName}（First Message）
                                  </div>
                                  <button
                                    type="button"
                                    className="rounded-md border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-zinc-700 hover:bg-zinc-50"
                                    onClick={() =>
                                      setEditingMsg({
                                        kind: "first",
                                        text: firstMessageText,
                                      })
                                    }
                                    disabled={sending}
                                    title="编辑这条 First Message（会同步到左侧 block）"
                                  >
                                    编辑
                                  </button>
                                </div>
                                {editingMsg?.kind === "first" ? (
                                  <div className="w-full rounded-2xl border border-zinc-200 bg-white p-2">
                                    <textarea
                                      className="min-h-24 w-full resize-y overflow-auto rounded-md border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                                      value={editingMsg.text}
                                      onChange={(e) =>
                                        setEditingMsg({
                                          kind: "first",
                                          text: e.target.value,
                                        })
                                      }
                                    />
                                    <div className="mt-2 flex justify-end gap-2">
                                      <button
                                        type="button"
                                        className="rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm hover:bg-zinc-50"
                                        onClick={cancelEdit}
                                      >
                                        取消
                                      </button>
                                      <button
                                        type="button"
                                        className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white hover:bg-zinc-800"
                                        onClick={saveEdit}
                                      >
                                        保存
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <>
                                    <div className="whitespace-pre-wrap rounded-2xl border border-zinc-200 bg-white px-3 py-2 text-sm">
                                      {firstMessageText}
                                    </div>
                                    <div className="mt-1 text-left text-[10px] text-zinc-400">
                                      {countTextStats(firstMessageText)}
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>
                          ) : null}
                          {chatHistory.map((m, idx) => (
                            <div
                              key={idx}
                              className={`flex ${
                                m.role === "user" ? "justify-end" : "justify-start"
                              }`}
                            >
                              <div
                                className={
                                  editingMsg?.kind === "history" &&
                                  editingMsg.index === idx
                                    ? "w-full max-w-[85%]"
                                    : "max-w-[85%]"
                                }
                              >
                                <div className="mb-1 flex items-center justify-between gap-2">
                                  <div
                                    className={`text-xs font-medium ${
                                      m.role === "user"
                                        ? "text-right text-zinc-600"
                                        : "text-left text-zinc-600"
                                    }`}
                                  >
                                    {m.role === "user" ? "你" : charDisplayName}
                                  </div>
                                  <div className="flex items-center gap-1">
                                    {m.role === "assistant" ? (
                                      <button
                                        type="button"
                                        className="rounded-md border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                                        onClick={() => void translateMessage(idx, m.content)}
                                        disabled={translatingIdx === idx || sending || !hasEnglish(m.content)}
                                        title={hasEnglish(m.content) ? "翻译成中文" : "未检测到英文"}
                                      >
                                        {translatingIdx === idx ? "翻译中…" : translations[idx] ? "重新翻译" : "翻译"}
                                      </button>
                                    ) : null}
                                    {idx === chatHistory.length - 1 &&
                                    m.role === "assistant" ? (
                                      <button
                                        type="button"
                                        className="rounded-md border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                                        onClick={() => void retryLastAi()}
                                        disabled={sending}
                                        title="重新请求：保留上一条用户输入，重建上下文并重新请求 API"
                                      >
                                        重新请求
                                      </button>
                                    ) : null}
                                    {m.role === "user" ? (
                                      <button
                                        type="button"
                                        className="rounded-md border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-red-700 hover:bg-zinc-50 disabled:opacity-50"
                                        onClick={() => retractFromUserMessage(idx)}
                                        disabled={sending}
                                        title="撤回这条用户消息，并删除其后的所有聊天记录"
                                      >
                                        撤回
                                      </button>
                                    ) : null}
                                    <button
                                      type="button"
                                      className="rounded-md border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                                      onClick={() => startEditHistory(idx)}
                                      disabled={sending}
                                      title="编辑这条消息（会影响后续上下文）"
                                    >
                                      编辑
                                    </button>
                                    <button
                                      type="button"
                                      className="rounded-md border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-red-600 hover:bg-red-50 hover:border-red-200 disabled:opacity-50"
                                      onClick={() => deleteMessage(idx)}
                                      disabled={sending}
                                      title="删除这条消息"
                                    >
                                      删除
                                    </button>
                                  </div>
                                </div>

                                {editingMsg?.kind === "history" &&
                                editingMsg.index === idx ? (
                                  <div className="w-full rounded-2xl border border-zinc-200 bg-white p-2">
                                    <textarea
                                      className="min-h-20 w-full resize-y overflow-auto rounded-md border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                                      value={editingMsg.text}
                                      onChange={(e) =>
                                        setEditingMsg({
                                          kind: "history",
                                          index: idx,
                                          text: e.target.value,
                                        })
                                      }
                                    />
                                    <div className="mt-2 flex justify-end gap-2">
                                      <button
                                        type="button"
                                        className="rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm hover:bg-zinc-50"
                                        onClick={cancelEdit}
                                      >
                                        取消
                                      </button>
                                      <button
                                        type="button"
                                        className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white hover:bg-zinc-800"
                                        onClick={saveEdit}
                                      >
                                        保存
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <>
                                    <div
                                      className={`whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
                                        m.role === "user"
                                          ? "bg-zinc-900 text-white"
                                          : "border border-zinc-200 bg-white text-zinc-950"
                                      }`}
                                    >
                                      {m.content}
                                    </div>
                                    {m.role === "assistant" && translations[idx] ? (
                                      <div className="mt-2 whitespace-pre-wrap rounded-2xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-zinc-800">
                                        <div className="mb-1 text-[10px] font-medium text-blue-600">翻译</div>
                                        {translations[idx]}
                                      </div>
                                    ) : null}
                                    <div
                                      className={`mt-1 text-[10px] text-zinc-400 ${
                                        m.role === "user" ? "text-right" : "text-left"
                                      }`}
                                    >
                                      {countTextStats(m.content)}
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>
                          ))}
                          {sending ? (
                            <div className="text-sm text-zinc-500">思考中…</div>
                          ) : null}
                          </div>
                        )}
                      </div>

                      {chatError ? (
                        <div className="px-3 pb-2">
                          <div className="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                            {chatError}
                          </div>
                        </div>
                      ) : null}

                      {/* input */}
                      <div className="px-3 pb-3">
                        {/* 快捷输入 */}
                        <div className="mb-2 flex items-center gap-2">
                          <button
                            type="button"
                            className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs text-zinc-700 hover:bg-zinc-50 hover:border-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            onClick={() => void sendMessage("(Continued)")}
                            disabled={sending || userAiSending}
                            title="发送 (Continued) 让 AI 继续"
                          >
                            (Continued)
                          </button>
                          <button
                            type="button"
                            className="rounded-full border border-indigo-300 bg-indigo-50 px-3 py-1 text-xs text-indigo-700 hover:bg-indigo-100 hover:border-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            onClick={() => void generateUserAiMessage()}
                            disabled={sending || userAiSending}
                            title="让AI模拟用户发送一条消息"
                          >
                            {userAiSending ? "用户AI思考中…" : "🤖 AI发送"}
                          </button>
                        </div>
                        <div className="relative rounded-2xl bg-gradient-to-r from-red-100 via-white to-emerald-100 p-[1px] shadow-sm">
                          <div className="flex items-end gap-2 rounded-2xl bg-white/90 p-2 backdrop-blur supports-[backdrop-filter]:bg-white/70 focus-within:ring-2 focus-within:ring-red-200">
                            <textarea
                              className="min-h-10 flex-1 resize-y rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-300"
                              placeholder="写点什么…（Cmd+Enter 发送）"
                              value={userInput}
                              onChange={(e) => setUserInput(e.target.value)}
                              onKeyDown={(e) => {
                                if (
                                  e.key === "Enter" &&
                                  (e.metaKey || e.ctrlKey)
                                ) {
                                  e.preventDefault();
                                  if (!sending) void sendMessage();
                                }
                              }}
                            />

                            <button
                              type="button"
                              className="h-10 shrink-0 rounded-xl bg-gradient-to-b from-zinc-900 to-zinc-800 px-4 text-sm font-medium text-white shadow-sm hover:from-zinc-800 hover:to-zinc-700 disabled:cursor-not-allowed disabled:opacity-50"
                              onClick={() => void sendMessage()}
                              disabled={sending || userAiSending || !userInput.trim()}
                              title="发送"
                            >
                              {sending ? "发送中…" : userAiSending ? "用户AI…" : "发送"}
                            </button>
                          </div>

                          <div className="pointer-events-none absolute -top-2 right-3 select-none text-sm text-red-300">
                            ❄
                          </div>
                          <div className="pointer-events-none absolute -top-2 right-7 select-none text-sm text-emerald-300">
                            ✦
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Prompt preview panel */}
              <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-zinc-200 bg-white">
                <div className="flex items-center justify-between border-b border-zinc-200 bg-zinc-50 px-4 py-2">
                  <div className="flex items-center gap-3">
                    <div className="text-sm font-medium">
                      最新请求：提示词展示
                    </div>
                    {lastPromptTokenCount > 0 && (
                      <div className="rounded-md bg-zinc-200 px-2 py-0.5 text-xs tabular-nums text-zinc-600">
                        ≈ {lastPromptTokenCount} tokens
                      </div>
                    )}
                    <select
                      className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs"
                      value={promptPreviewMode}
                      onChange={(e) =>
                        setPromptPreviewMode(
                          e.target.value as "concat" | "langsmith" | "openrouter",
                        )
                      }
                      title="选择提示词拼接/展示方式"
                    >
                      <option value="concat">拼接（单 system）</option>
                      <option value="langsmith">LangSmith（多 system）</option>
                      <option value="openrouter">OpenRouter（完整请求）</option>
                    </select>
                  </div>
                  <button
                    type="button"
                    className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50 disabled:opacity-50"
                    onClick={async () => {
                      if (!lastPromptPreviewForPanel) return;
                      try {
                        await navigator.clipboard.writeText(lastPromptPreviewForPanel);
                      } catch {
                        // ignore
                      }
                    }}
                    disabled={!lastPromptPreviewForPanel}
                  >
                    复制
                  </button>
                </div>
                <pre className="min-h-0 flex-1 overflow-auto p-4 text-xs text-zinc-800">
                  {lastPromptPreviewForPanel || "（暂无：发送一条消息后会生成）"}
                </pre>
              </div>
        </div>
          </section>
      </div>

        {showPayload ? (
          <div className="fixed inset-0 z-50 bg-black/40 p-4">
            <div className="mx-auto flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-lg bg-white shadow-xl">
              <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                <div className="text-sm font-semibold">请求/响应 Payload</div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm hover:bg-zinc-50 disabled:opacity-50"
                    onClick={async () => {
                      const text = JSON.stringify(
                        { request: lastRequest, response: lastResponse },
                        null,
                        2,
                      );
                      try {
                        await navigator.clipboard.writeText(text);
                      } catch {
                        // ignore
                      }
                    }}
                    disabled={!lastRequest && !lastResponse}
                  >
                    复制 JSON
                  </button>
                  <button
                    type="button"
                    className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white hover:bg-zinc-800"
                    onClick={() => setShowPayload(false)}
                  >
                    关闭
                  </button>
                </div>
              </div>

              <div className="grid flex-1 grid-cols-2 gap-0 overflow-hidden">
                <div className="flex h-full flex-col overflow-hidden border-r border-zinc-200">
                  <div className="border-b border-zinc-200 bg-zinc-50 px-4 py-2 text-xs font-medium text-zinc-700">
                    Request
                  </div>
                  <pre className="flex-1 overflow-auto p-4 text-xs text-zinc-800">
                    {lastRequest
                      ? JSON.stringify(
                          { headers: lastHeaders, body: lastRequest },
                          null,
                          2,
                        )
                      : "（暂无）"}
                  </pre>
                </div>
                <div className="flex h-full flex-col overflow-hidden">
                  <div className="border-b border-zinc-200 bg-zinc-50 px-4 py-2 text-xs font-medium text-zinc-700">
                    Response
                  </div>
                  <pre className="flex-1 overflow-auto p-4 text-xs text-zinc-800">
                    {lastResponse ? JSON.stringify(lastResponse, null, 2) : "（暂无）"}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {showDiff && diffTarget ? (
          <div className="fixed inset-0 z-50 bg-black/40 p-4">
            <div className="mx-auto flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-lg bg-white shadow-xl">
              <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                <div className="text-sm font-semibold">
                  Diff：当前 vs {diffTarget.name}
                </div>
                <button
                  type="button"
                  className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white hover:bg-zinc-800"
                  onClick={() => setShowDiff(false)}
                >
                  关闭
                </button>
              </div>

              <div className="grid flex-1 grid-cols-2 gap-0 overflow-hidden">
                <div className="flex h-full flex-col overflow-hidden border-r border-zinc-200">
                  <div className="border-b border-zinc-200 bg-zinc-50 px-4 py-2 text-xs font-medium text-zinc-700">
                    当前
                  </div>
                  <pre className="flex-1 overflow-auto p-4 text-xs text-zinc-800">
                    {JSON.stringify(promptDraft, null, 2)}
                  </pre>
                </div>
                <div className="flex h-full flex-col overflow-hidden">
                  <div className="border-b border-zinc-200 bg-zinc-50 px-4 py-2 text-xs font-medium text-zinc-700">
                    {diffTarget.name}
                  </div>
                  <pre className="flex-1 overflow-auto p-4 text-xs text-zinc-800">
                    {JSON.stringify(diffTarget.prompt, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
