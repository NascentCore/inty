"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createOpenRouterChatCompletion,
  fetchOpenRouterModels,
  type OpenRouterMessage,
  type OpenRouterModel,
} from "@/lib/openrouter";
import { useLocalStorageState } from "@/lib/useLocalStorageState";

const LS_API_KEY = "mychatplayground.openrouter.apiKey";
const LS_MODEL_ID = "mychatplayground.promptBlockTest.modelId";
const LS_PROMPT_BLOCKS = "mychatplayground.promptBlockTest.promptBlocks";
const LS_TEST_MESSAGES = "mychatplayground.promptBlockTest.testMessages";
const LS_TEST_MODE = "mychatplayground.promptBlockTest.testMode";

type PromptBlock = {
  id: string;
  type: "system" | "assistant" | "user";
  content: string;
  isVariable: boolean;
  order: number;
};

type TestMessage = {
  id: string;
  content: string;
  order: number;
};

type TestResultItem = {
  messageId: string;
  userMessage: string;
  aiReply: string;
  timestamp: string;
  status: "pending" | "loading" | "success" | "error";
  error?: string;
};

type TestSession = {
  groupType: "A" | "B";
  testMode: "single" | "multi";
  modelId: string;
  results: TestResultItem[];
  status: "idle" | "running" | "completed" | "error";
};

const DEFAULT_PROMPT_BLOCKS: PromptBlock[] = [
  {
    id: "block-system-1",
    type: "system",
    content: "You are a friendly AI companion.",
    isVariable: false,
    order: 1,
  },
  {
    id: "block-system-var",
    type: "system",
    content: "## 关于这位用户...\n（这里放入用户画像/记忆）",
    isVariable: true,
    order: 2,
  },
  {
    id: "block-assistant-1",
    type: "assistant",
    content: "Hello! How can I help you today?",
    isVariable: false,
    order: 3,
  },
  {
    id: "block-user-1",
    type: "user",
    content: "Hey! Nice to meet you!",
    isVariable: false,
    order: 4,
  },
];

const DEFAULT_TEST_MESSAGES: TestMessage[] = [
  { id: "test-1", content: "Hey! Nice to meet you~", order: 1 },
  { id: "test-2", content: "I've been feeling stressed lately...", order: 2 },
  { id: "test-3", content: "What should I do this weekend?", order: 3 },
];

const TYPE_OPTIONS: Array<{ value: PromptBlock["type"]; label: string }> = [
  { value: "system", label: "System" },
  { value: "assistant", label: "AI" },
  { value: "user", label: "Human" },
];

const getId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

function normalizeBlocks(raw: PromptBlock[]): PromptBlock[] {
  const normalized = raw
    .map((b, idx) => ({
      id: typeof b?.id === "string" ? b.id : `block-${idx}`,
      type:
        b?.type === "system" || b?.type === "assistant" || b?.type === "user"
          ? b.type
          : "system",
      content: typeof b?.content === "string" ? b.content : "",
      isVariable: Boolean(b?.isVariable),
      order: typeof b?.order === "number" ? b.order : idx + 1,
    }))
    .sort((a, b) => a.order - b.order)
    .map((b, idx) => ({ ...b, order: idx + 1 }));

  let variableFound = false;
  return normalized.map((b) => {
    if (!b.isVariable) return b;
    if (!variableFound) {
      variableFound = true;
      return b;
    }
    return { ...b, isVariable: false };
  });
}

function normalizeTestMessages(raw: TestMessage[]): TestMessage[] {
  return raw
    .map((m, idx) => ({
      id: typeof m?.id === "string" ? m.id : `msg-${idx}`,
      content: typeof m?.content === "string" ? m.content : "",
      order: typeof m?.order === "number" ? m.order : idx + 1,
    }))
    .sort((a, b) => a.order - b.order)
    .map((m, idx) => ({ ...m, order: idx + 1 }));
}

function buildBaseMessages(
  blocks: PromptBlock[],
  includeVariable: boolean
): OpenRouterMessage[] {
  return blocks
    .filter((block) => includeVariable || !block.isVariable)
    .sort((a, b) => a.order - b.order)
    .map((block) => ({
      role: block.type,
      content: block.content,
    }));
}

function downloadText(filename: string, text: string, mime = "text/plain") {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function PromptBlockTestPage() {
  const [apiKey] = useLocalStorageState<string>(LS_API_KEY, "");
  const [modelId, setModelId] = useLocalStorageState<string>(LS_MODEL_ID, "");
  const [promptBlocks, setPromptBlocks] = useLocalStorageState<PromptBlock[]>(
    LS_PROMPT_BLOCKS,
    DEFAULT_PROMPT_BLOCKS
  );
  const [testMessages, setTestMessages] = useLocalStorageState<TestMessage[]>(
    LS_TEST_MESSAGES,
    DEFAULT_TEST_MESSAGES
  );
  const [testMode, setTestMode] = useLocalStorageState<"single" | "multi">(
    LS_TEST_MODE,
    "single"
  );

  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const prevApiKeyRef = useRef<string>("");

  const [sessions, setSessions] = useState<{ A: TestSession; B: TestSession }>(
    () => ({
      A: {
        groupType: "A",
        testMode,
        modelId,
        results: [],
        status: "idle",
      },
      B: {
        groupType: "B",
        testMode,
        modelId,
        results: [],
        status: "idle",
      },
    })
  );
  const [runError, setRunError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingMessageText, setEditingMessageText] = useState("");
  const lastRunRef = useRef<{
    blocks: PromptBlock[];
    testMessages: TestMessage[];
    testMode: "single" | "multi";
    modelId: string;
  } | null>(null);

  useEffect(() => {
    const normalized = normalizeBlocks(promptBlocks);
    if (JSON.stringify(normalized) !== JSON.stringify(promptBlocks)) {
      setPromptBlocks(normalized);
    }
  }, [promptBlocks, setPromptBlocks]);

  useEffect(() => {
    const normalized = normalizeTestMessages(testMessages);
    if (JSON.stringify(normalized) !== JSON.stringify(testMessages)) {
      setTestMessages(normalized);
    }
  }, [testMessages, setTestMessages]);

  const sortedBlocks = useMemo(
    () => [...promptBlocks].sort((a, b) => a.order - b.order),
    [promptBlocks]
  );
  const sortedTestMessages = useMemo(
    () => [...testMessages].sort((a, b) => a.order - b.order),
    [testMessages]
  );

  const baseMessagesA = useMemo(
    () => buildBaseMessages(sortedBlocks, false),
    [sortedBlocks]
  );
  const baseMessagesB = useMemo(
    () => buildBaseMessages(sortedBlocks, true),
    [sortedBlocks]
  );

  const loadModels = useCallback(async () => {
    if (!apiKey) return;
    setModelsLoading(true);
    setModelsError(null);
    try {
      const data = await fetchOpenRouterModels(apiKey);
      setModels(data);
      if (!modelId && data.length > 0) {
        setModelId(data[0]!.id);
      }
    } catch (e) {
      setModelsError(e instanceof Error ? e.message : String(e));
    } finally {
      setModelsLoading(false);
    }
  }, [apiKey, modelId, setModelId]);

  useEffect(() => {
    const prev = prevApiKeyRef.current;
    prevApiKeyRef.current = apiKey;
    if (!prev && apiKey) {
      void loadModels();
    }
  }, [apiKey, loadModels]);

  const updateSession = useCallback(
    (groupType: "A" | "B", updater: (prev: TestSession) => TestSession) => {
      setSessions((prev) => ({
        ...prev,
        [groupType]: updater(prev[groupType]),
      }));
    },
    []
  );

  const appendResult = useCallback(
    (groupType: "A" | "B", item: TestResultItem) => {
      updateSession(groupType, (prev) => ({
        ...prev,
        results: [...prev.results, item],
      }));
    },
    [updateSession]
  );

  const patchResult = useCallback(
    (
      groupType: "A" | "B",
      messageId: string,
      patch: Partial<TestResultItem>
    ) => {
      updateSession(groupType, (prev) => ({
        ...prev,
        results: prev.results.map((r) =>
          r.messageId === messageId ? { ...r, ...patch } : r
        ),
      }));
    },
    [updateSession]
  );

  const moveBlock = (id: string, direction: -1 | 1) => {
    setPromptBlocks((prev) => {
      const sorted = [...prev].sort((a, b) => a.order - b.order);
      const idx = sorted.findIndex((b) => b.id === id);
      const nextIdx = idx + direction;
      if (idx < 0 || nextIdx < 0 || nextIdx >= sorted.length) return prev;
      const temp = sorted[idx]!;
      sorted[idx] = sorted[nextIdx]!;
      sorted[nextIdx] = temp;
      return normalizeBlocks(sorted);
    });
  };

  const toggleVariable = (id: string) => {
    setPromptBlocks((prev) => {
      const target = prev.find((b) => b.id === id);
      const nextIsVariable = !target?.isVariable;
      return prev.map((b) => {
        if (b.id === id) {
          return { ...b, isVariable: nextIsVariable };
        }
        if (nextIsVariable) return { ...b, isVariable: false };
        return b;
      });
    });
  };

  const addBlock = () => {
    setPromptBlocks((prev) =>
      normalizeBlocks([
        ...prev,
        {
          id: getId(),
          type: "system",
          content: "",
          isVariable: false,
          order: prev.length + 1,
        },
      ])
    );
  };

  const removeBlock = (id: string) => {
    setPromptBlocks((prev) => normalizeBlocks(prev.filter((b) => b.id !== id)));
  };

  const moveTestMessage = (id: string, direction: -1 | 1) => {
    setTestMessages((prev) => {
      const sorted = [...prev].sort((a, b) => a.order - b.order);
      const idx = sorted.findIndex((m) => m.id === id);
      const nextIdx = idx + direction;
      if (idx < 0 || nextIdx < 0 || nextIdx >= sorted.length) return prev;
      const temp = sorted[idx]!;
      sorted[idx] = sorted[nextIdx]!;
      sorted[nextIdx] = temp;
      return normalizeTestMessages(sorted);
    });
  };

  const addTestMessage = () => {
    setTestMessages((prev) =>
      normalizeTestMessages([
        ...prev,
        { id: getId(), content: "", order: prev.length + 1 },
      ])
    );
  };

  const removeTestMessage = (id: string) => {
    setTestMessages((prev) =>
      normalizeTestMessages(prev.filter((m) => m.id !== id))
    );
  };

  const runGroup = useCallback(
    async (groupType: "A" | "B") => {
      const includeVariable = groupType === "B";
      const baseMessages = buildBaseMessages(sortedBlocks, includeVariable);
      const sortedTests = [...sortedTestMessages].sort(
        (a, b) => a.order - b.order
      );

      updateSession(groupType, () => ({
        groupType,
        testMode,
        modelId,
        results: [],
        status: "running",
      }));

      let hasError = false;

      if (testMode === "single") {
        for (const testMsg of sortedTests) {
          const item: TestResultItem = {
            messageId: testMsg.id,
            userMessage: testMsg.content,
            aiReply: "",
            timestamp: new Date().toISOString(),
            status: "loading",
          };
          appendResult(groupType, item);

          try {
            const resp = await createOpenRouterChatCompletion({
              apiKey: apiKey.trim(),
              request: {
                model: modelId,
                messages: [
                  ...baseMessages,
                  { role: "user", content: testMsg.content },
                ],
                temperature: 0.7,
                max_tokens: 500,
              },
              siteUrl:
                typeof window !== "undefined"
                  ? window.location.origin
                  : undefined,
              appName: "mychatplayground-prompt-block-test",
            });
            const content = resp.choices?.[0]?.message?.content || "";
            patchResult(groupType, testMsg.id, {
              aiReply: content,
              status: "success",
              timestamp: new Date().toISOString(),
            });
          } catch (e) {
            hasError = true;
            patchResult(groupType, testMsg.id, {
              status: "error",
              error: e instanceof Error ? e.message : String(e),
              timestamp: new Date().toISOString(),
            });
          }
        }
      } else {
        const conversationHistory: OpenRouterMessage[] = [...baseMessages];
        for (const testMsg of sortedTests) {
          conversationHistory.push({
            role: "user",
            content: testMsg.content,
          });

          const item: TestResultItem = {
            messageId: testMsg.id,
            userMessage: testMsg.content,
            aiReply: "",
            timestamp: new Date().toISOString(),
            status: "loading",
          };
          appendResult(groupType, item);

          try {
            const resp = await createOpenRouterChatCompletion({
              apiKey: apiKey.trim(),
              request: {
                model: modelId,
                messages: [...conversationHistory],
                temperature: 0.7,
                max_tokens: 500,
              },
              siteUrl:
                typeof window !== "undefined"
                  ? window.location.origin
                  : undefined,
              appName: "mychatplayground-prompt-block-test",
            });
            const content = resp.choices?.[0]?.message?.content || "";
            conversationHistory.push({ role: "assistant", content });
            patchResult(groupType, testMsg.id, {
              aiReply: content,
              status: "success",
              timestamp: new Date().toISOString(),
            });
          } catch (e) {
            hasError = true;
            patchResult(groupType, testMsg.id, {
              status: "error",
              error: e instanceof Error ? e.message : String(e),
              timestamp: new Date().toISOString(),
            });
            break;
          }
        }
      }

      updateSession(groupType, (prev) => ({
        ...prev,
        status: hasError ? "error" : "completed",
      }));
    },
    [
      apiKey,
      appendResult,
      modelId,
      patchResult,
      sortedBlocks,
      sortedTestMessages,
      testMode,
      updateSession,
    ]
  );

  const runABTest = async () => {
    setRunError(null);
    if (!apiKey.trim()) {
      setRunError("请先在主页填写 OpenRouter API Key");
      return;
    }
    if (!modelId) {
      setRunError("请先选择模型");
      return;
    }
    if (sortedTestMessages.length === 0) {
      setRunError("请至少添加一条测试消息");
      return;
    }

    lastRunRef.current = {
      blocks: sortedBlocks,
      testMessages: sortedTestMessages,
      testMode,
      modelId,
    };

    await Promise.all([runGroup("A"), runGroup("B")]);
  };

  const retryGroup = async (groupType: "A" | "B") => {
    if (!lastRunRef.current) {
      await runABTest();
      return;
    }
    await runGroup(groupType);
  };

  const retrySingleItem = async (groupType: "A" | "B", item: TestResultItem) => {
    if (testMode !== "single") return;
    const includeVariable = groupType === "B";
    const baseMessages = buildBaseMessages(sortedBlocks, includeVariable);
    patchResult(groupType, item.messageId, {
      status: "loading",
      error: undefined,
      timestamp: new Date().toISOString(),
    });
    try {
      const resp = await createOpenRouterChatCompletion({
        apiKey: apiKey.trim(),
        request: {
          model: modelId,
          messages: [
            ...baseMessages,
            { role: "user", content: item.userMessage },
          ],
          temperature: 0.7,
          max_tokens: 500,
        },
        siteUrl:
          typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground-prompt-block-test",
      });
      const content = resp.choices?.[0]?.message?.content || "";
      patchResult(groupType, item.messageId, {
        aiReply: content,
        status: "success",
        timestamp: new Date().toISOString(),
      });
    } catch (e) {
      patchResult(groupType, item.messageId, {
        status: "error",
        error: e instanceof Error ? e.message : String(e),
        timestamp: new Date().toISOString(),
      });
    }
  };

  const exportJson = () => {
    const payload = {
      schema: "mychatplayground.promptBlockTest.export.v1",
      exportedAt: Date.now(),
      modelId,
      testMode,
      promptBlocks: sortedBlocks,
      testMessages: sortedTestMessages,
      sessions,
    };
    downloadText(
      `prompt-block-test-${new Date().toISOString().slice(0, 19)}.json`,
      JSON.stringify(payload, null, 2),
      "application/json"
    );
  };

  const exportMarkdown = () => {
    const lines: string[] = [];
    lines.push("# 提示词板块 A/B 对比测试结果");
    lines.push("");
    lines.push(`- 导出时间：${new Date().toLocaleString()}`);
    lines.push(`- 模型：${modelId || "（未选择）"}`);
    lines.push(`- 测试模式：${testMode === "single" ? "单轮独立测试" : "多轮脚本测试"}`);
    lines.push("");
    lines.push("## 提示词板块");
    sortedBlocks.forEach((b, idx) => {
      lines.push(
        `- ${idx + 1}. [${b.type}]${b.isVariable ? " ⭐变量" : ""} ${b.content}`
      );
    });
    lines.push("");
    lines.push("## 测试消息");
    sortedTestMessages.forEach((m, idx) => {
      lines.push(`- ${idx + 1}. ${m.content}`);
    });
    lines.push("");
    (["A", "B"] as const).forEach((group) => {
      const session = sessions[group];
      lines.push(`## ${group} 组结果`);
      lines.push(`- 状态：${session.status}`);
      lines.push(`- 结果条数：${session.results.length}`);
      lines.push("");
      session.results.forEach((r, idx) => {
        lines.push(`### 问题 ${idx + 1}`);
        lines.push(`- 用户：${r.userMessage}`);
        if (r.status === "success") {
          lines.push(`- AI：${r.aiReply}`);
        } else if (r.status === "loading") {
          lines.push("- AI：请求中...");
        } else if (r.status === "error") {
          lines.push(`- AI：失败（${r.error || "未知错误"}）`);
        } else {
          lines.push("- AI：未开始");
        }
        lines.push("");
      });
    });
    downloadText(
      `prompt-block-test-${new Date().toISOString().slice(0, 19)}.md`,
      lines.join("\n"),
      "text/markdown"
    );
  };

  const hasRunning =
    sessions.A.status === "running" || sessions.B.status === "running";

  return (
    <div className="h-full w-full bg-zinc-50 text-zinc-900">
      <div className="mx-auto flex h-full w-full max-w-6xl flex-col gap-4 p-4">
        <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">模型选择</div>
            <button
              type="button"
              className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50 disabled:opacity-50"
              onClick={loadModels}
              disabled={modelsLoading || !apiKey}
            >
              {modelsLoading ? "加载中..." : "刷新模型列表"}
            </button>
          </div>
          {!apiKey && (
            <div className="mb-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
              请先在主页填写 OpenRouter API Key
            </div>
          )}
          {modelsError && (
            <div className="mb-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
              {modelsError}
            </div>
          )}
          <select
            className="w-full rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            disabled={models.length === 0}
          >
            {models.length === 0 ? (
              <option value="">
                {apiKey ? "（未加载模型列表）" : "（先填写 API Key）"}
              </option>
            ) : null}
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.id}
              </option>
            ))}
          </select>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">提示词板块编辑区</div>
            <button
              type="button"
              className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
              onClick={addBlock}
            >
              + 添加板块
            </button>
          </div>
          <div className="space-y-3">
            {sortedBlocks.map((block, idx) => (
              <div
                key={block.id}
                className={`rounded-md border p-3 ${
                  block.isVariable
                    ? "border-amber-300 bg-amber-50/50"
                    : "border-zinc-200 bg-white"
                }`}
              >
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <select
                      className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs"
                      value={block.type}
                      onChange={(e) =>
                        setPromptBlocks((prev) =>
                          prev.map((b) =>
                            b.id === block.id
                              ? {
                                  ...b,
                                  type: e.target.value as PromptBlock["type"],
                                }
                              : b
                          )
                        )
                      }
                    >
                      {TYPE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <label className="flex items-center gap-1 text-xs text-zinc-600">
                      <input
                        type="checkbox"
                        checked={block.isVariable}
                        onChange={() => toggleVariable(block.id)}
                      />
                      变量板块
                    </label>
                    {block.isVariable && (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-700">
                        ⭐ 仅 B 组包含
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50 disabled:opacity-50"
                      onClick={() => moveBlock(block.id, -1)}
                      disabled={idx === 0}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50 disabled:opacity-50"
                      onClick={() => moveBlock(block.id, 1)}
                      disabled={idx === sortedBlocks.length - 1}
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                      onClick={() => removeBlock(block.id)}
                    >
                      ×
                    </button>
                  </div>
                </div>
                <textarea
                  className="min-h-20 w-full resize-y rounded-md border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  value={block.content}
                  onChange={(e) =>
                    setPromptBlocks((prev) =>
                      prev.map((b) =>
                        b.id === block.id
                          ? { ...b, content: e.target.value }
                          : b
                      )
                    )
                  }
                  placeholder="输入板块内容..."
                />
              </div>
            ))}
          </div>

          <div className="mt-3 rounded-md border border-dashed border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
            消息预览：A 组 [{baseMessagesA.length}条消息] | B 组 [
            {baseMessagesB.length}条消息]
            <button
              type="button"
              className="ml-2 text-xs text-indigo-600 hover:text-indigo-700"
              onClick={() => setShowPreview((v) => !v)}
            >
              {showPreview ? "收起查看" : "展开查看"}
            </button>
          </div>
          {showPreview && (
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
              <pre className="max-h-56 overflow-auto rounded-md border border-zinc-200 bg-white p-3 text-xs">
                {JSON.stringify(baseMessagesA, null, 2)}
              </pre>
              <pre className="max-h-56 overflow-auto rounded-md border border-zinc-200 bg-white p-3 text-xs">
                {JSON.stringify(baseMessagesB, null, 2)}
              </pre>
            </div>
          )}
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">测试模式</div>
            <div className="text-xs text-zinc-500">
              {testMode === "single"
                ? "单轮独立测试"
                : "多轮脚本测试"}
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="testMode"
                value="single"
                checked={testMode === "single"}
                onChange={() => setTestMode("single")}
              />
              单轮独立测试
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="testMode"
                value="multi"
                checked={testMode === "multi"}
                onChange={() => setTestMode("multi")}
              />
              多轮脚本测试
            </label>
          </div>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">测试消息列表</div>
            <button
              type="button"
              className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
              onClick={addTestMessage}
            >
              + 添加测试消息
            </button>
          </div>
          <div className="space-y-2">
            {sortedTestMessages.map((msg, idx) => (
              <div
                key={msg.id}
                className="flex flex-col gap-2 rounded-md border border-zinc-200 bg-white p-3 md:flex-row md:items-center"
              >
                <div className="text-xs text-zinc-400">[{idx + 1}]</div>
                <div className="flex-1 text-sm">
                  {editingMessageId === msg.id ? (
                    <textarea
                      className="w-full resize-y rounded-md border border-zinc-200 px-2 py-1 text-sm outline-none focus:border-zinc-400"
                      value={editingMessageText}
                      onChange={(e) => setEditingMessageText(e.target.value)}
                    />
                  ) : (
                    <div className="whitespace-pre-wrap text-sm text-zinc-800">
                      {msg.content || "（空）"}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {editingMessageId === msg.id ? (
                    <>
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
                        onClick={() => {
                          setTestMessages((prev) =>
                            prev.map((m) =>
                              m.id === msg.id
                                ? { ...m, content: editingMessageText }
                                : m
                            )
                          );
                          setEditingMessageId(null);
                        }}
                      >
                        保存
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
                        onClick={() => setEditingMessageId(null)}
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50"
                        onClick={() => {
                          setEditingMessageId(msg.id);
                          setEditingMessageText(msg.content);
                        }}
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50 disabled:opacity-50"
                        onClick={() => moveTestMessage(msg.id, -1)}
                        disabled={idx === 0}
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs hover:bg-zinc-50 disabled:opacity-50"
                        onClick={() => moveTestMessage(msg.id, 1)}
                        disabled={idx === sortedTestMessages.length - 1}
                      >
                        ↓
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                        onClick={() => removeTestMessage(msg.id)}
                      >
                        ×
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="text-sm text-zinc-600">
              点击开始后将同时并行执行 A/B 组测试
            </div>
            <div className="flex items-center gap-2">
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
                onClick={exportMarkdown}
              >
                导出 Markdown
              </button>
              <button
                type="button"
                className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
                onClick={runABTest}
                disabled={hasRunning}
              >
                ▶ 开始 A/B 对比测试
              </button>
            </div>
          </div>
          {runError && (
            <div className="mt-3 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
              {runError}
            </div>
          )}
        </section>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {(["A", "B"] as const).map((group) => {
            const session = sessions[group];
            const completed = session.results.filter(
              (r) => r.status === "success" || r.status === "error"
            ).length;
            const total = sortedTestMessages.length;
            const statusLabel =
              session.status === "idle"
                ? "未开始"
                : session.status === "running"
                ? "进行中"
                : session.status === "error"
                ? "出错"
                : "已完成";
            return (
              <div
                key={group}
                className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm"
              >
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-semibold">
                      {group} 组结果（{group === "A" ? "不含变量板块" : "含变量板块"}
                      ）
                    </div>
                    <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] text-zinc-600">
                      {statusLabel}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-zinc-500">
                    <span>
                      {completed}/{total}
                    </span>
                    {session.status !== "running" && session.results.length > 0 && (
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-[11px] hover:bg-zinc-50"
                        onClick={() => retryGroup(group)}
                      >
                        重新测试
                      </button>
                    )}
                    {session.status === "error" && (
                      <button
                        type="button"
                        className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-[11px] text-amber-700 hover:bg-amber-100"
                        onClick={() => retryGroup(group)}
                      >
                        重试本组
                      </button>
                    )}
                  </div>
                </div>

                {session.results.length === 0 ? (
                  <div className="rounded-md border border-dashed border-zinc-200 bg-zinc-50 px-3 py-6 text-center text-xs text-zinc-500">
                    暂无结果，点击上方开始测试
                  </div>
                ) : testMode === "single" ? (
                  <div className="space-y-3">
                    {session.results.map((r, idx) => (
                      <div
                        key={r.messageId}
                        className="rounded-md border border-zinc-200 bg-white p-3"
                      >
                        <div className="mb-2 text-xs text-zinc-500">
                          问题 {idx + 1}
                        </div>
                        <div className="mb-2 rounded-md bg-zinc-900 px-3 py-2 text-sm text-white">
                          👤 {r.userMessage}
                        </div>
                        {r.status === "loading" ? (
                          <div className="rounded-md bg-zinc-50 px-3 py-2 text-sm text-zinc-600">
                            🤖 请求中...
                          </div>
                        ) : r.status === "error" ? (
                          <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                            🤖 失败：{r.error || "未知错误"}
                          </div>
                        ) : (
                          <div className="whitespace-pre-wrap rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-800">
                            🤖 {r.aiReply || "（空回复）"}
                          </div>
                        )}
                        {r.status === "error" && (
                          <div className="mt-2 flex justify-end">
                            <button
                              type="button"
                              className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-[11px] hover:bg-zinc-50"
                              onClick={() => void retrySingleItem(group, r)}
                            >
                              重试该条
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {session.results.map((r) => (
                      <div key={r.messageId} className="space-y-2">
                        <div className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white">
                          👤 {r.userMessage}
                        </div>
                        {r.status === "loading" ? (
                          <div className="rounded-md bg-zinc-50 px-3 py-2 text-sm text-zinc-600">
                            🤖 请求中...
                          </div>
                        ) : r.status === "error" ? (
                          <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                            🤖 失败：{r.error || "未知错误"}
                          </div>
                        ) : (
                          <div className="whitespace-pre-wrap rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-800">
                            🤖 {r.aiReply || "（空回复）"}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </section>
      </div>
    </div>
  );
}

