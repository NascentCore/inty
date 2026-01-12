"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  createOpenRouterChatCompletion,
  fetchOpenRouterModels,
  type OpenRouterModel,
} from "@/lib/openrouter";
import { useLocalStorageState } from "@/lib/useLocalStorageState";

const LS_API_KEY = "mychatplayground.openrouter.apiKey";
const LS_ANALYSIS_MODEL = "mychatplayground.conversationAnalysis.modelId";
const LS_ANALYSIS_PROMPT = "mychatplayground.conversationAnalysis.prompt";

// 预设分析提示词
const PRESET_PROMPTS = [
  {
    name: "用户分析",
    prompt: `请分析以下对话内容，提供：
1. 用户的主要表达习惯。
2. 根据对话内容，提炼及推测关于用户本人的客观事实信息。
3. 根据时间信息推测用户（默认为美国用户）的使用习惯。
4. 对话主题的概要（按时间发生顺序总结）

请用清晰的结构化格式输出分析结果。`,
  },
  {
    name: "对话摘要",
    prompt: `请分析以下对话内容，提供：
1. 对话主题概要
2. 参与者主要观点
3. 关键结论或决定
4. 后续行动项（如有）

请用清晰的结构化格式输出分析结果。`,
  },
];

const DEFAULT_PROMPT = PRESET_PROMPTS[0].prompt;

// 格式化上下文长度
function formatContextLength(contextLength?: number): string {
  if (!contextLength) return "";
  if (contextLength >= 1000000) {
    return `${(contextLength / 1000000).toFixed(1)}M`;
  }
  if (contextLength >= 1000) {
    return `${Math.round(contextLength / 1000)}K`;
  }
  return String(contextLength);
}

// 估算 token 数量
function estimateTokens(text: string): number {
  // 简单估算：英文约 0.75 token/word，中文约 1.5 token/字
  const words = text.split(/\s+/).length;
  const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
  return Math.ceil(words * 0.75 + chineseChars * 1.5);
}

// 格式化 token 数量
function formatTokens(tokens: number): string {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`;
  }
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}K`;
  }
  return String(tokens);
}

export default function ConversationAnalysisPage() {
  const [apiKey] = useLocalStorageState<string>(LS_API_KEY, "");
  const [selectedModelId, setSelectedModelId] = useLocalStorageState<string>(
    LS_ANALYSIS_MODEL,
    ""
  );
  const [analysisPrompt, setAnalysisPrompt] = useLocalStorageState<string>(
    LS_ANALYSIS_PROMPT,
    DEFAULT_PROMPT
  );

  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  // 文件相关状态
  const [fileName, setFileName] = useState<string>("");
  const [fileContent, setFileContent] = useState<string>("");
  const [fileError, setFileError] = useState<string | null>(null);

  // 分析相关状态
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<string>("");
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const prevApiKeyRef = useRef<string>("");

  // 加载模型列表
  const loadModels = useCallback(async () => {
    if (!apiKey) return;
    setModelsLoading(true);
    setModelsError(null);
    try {
      const data = await fetchOpenRouterModels(apiKey);
      // 按上下文长度降序排序
      data.sort((a, b) => (b.context_length || 0) - (a.context_length || 0));
      setModels(data);
      // 如果没有选择模型，默认选第一个
      if (!selectedModelId && data.length > 0) {
        setSelectedModelId(data[0]!.id);
      }
    } catch (e) {
      setModelsError(e instanceof Error ? e.message : String(e));
    } finally {
      setModelsLoading(false);
    }
  }, [apiKey, selectedModelId, setSelectedModelId]);

  useEffect(() => {
    const prev = prevApiKeyRef.current;
    prevApiKeyRef.current = apiKey;
    if (!prev && apiKey) {
      void loadModels();
    }
  }, [apiKey, loadModels]);

  // 处理文件上传
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".txt") && !file.name.endsWith(".csv")) {
      setFileError("请上传 .txt 或 .csv 文件");
      return;
    }

    setFileError(null);
    setFileName(file.name);

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setFileContent(content);
      // 清空之前的分析结果
      setAnalysisResult("");
      setAnalysisError(null);
    };
    reader.onerror = () => {
      setFileError("文件读取失败");
    };
    reader.readAsText(file);
  };

  // 处理拖拽上传
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".txt") && !file.name.endsWith(".csv")) {
      setFileError("请上传 .txt 或 .csv 文件");
      return;
    }

    setFileError(null);
    setFileName(file.name);

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setFileContent(content);
      setAnalysisResult("");
      setAnalysisError(null);
    };
    reader.onerror = () => {
      setFileError("文件读取失败");
    };
    reader.readAsText(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  // 开始分析
  const handleAnalyze = async () => {
    if (!fileContent.trim()) {
      setAnalysisError("请先上传文件");
      return;
    }
    if (!apiKey.trim()) {
      setAnalysisError("请先在主页填写 API Key");
      return;
    }
    if (!selectedModelId) {
      setAnalysisError("请先选择模型");
      return;
    }

    setAnalyzing(true);
    setAnalysisResult("");
    setAnalysisError(null);

    try {
      const resp = await createOpenRouterChatCompletion({
        apiKey: apiKey.trim(),
        request: {
          model: selectedModelId,
          messages: [
            { role: "system", content: analysisPrompt },
            { role: "user", content: fileContent },
          ],
          temperature: 0.3,
          max_tokens: 4000,
        },
        siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground-conversation-analysis",
      });

      const content = resp.choices?.[0]?.message?.content;
      const output = typeof content === "string" ? content.trim() : "";
      setAnalysisResult(output);
    } catch (e) {
      setAnalysisError(e instanceof Error ? e.message : String(e));
    } finally {
      setAnalyzing(false);
    }
  };

  // 应用预设提示词
  const applyPreset = (prompt: string) => {
    setAnalysisPrompt(prompt);
  };

  // 复制结果
  const copyResult = async () => {
    try {
      await navigator.clipboard.writeText(analysisResult);
    } catch {
      // ignore
    }
  };

  // 清空文件
  const clearFile = () => {
    setFileName("");
    setFileContent("");
    setFileError(null);
    setAnalysisResult("");
    setAnalysisError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // 计算文件 token 数
  const fileTokens = fileContent ? estimateTokens(fileContent) : 0;
  const selectedModel = models.find((m) => m.id === selectedModelId);
  const modelContext = selectedModel?.context_length || 0;
  const isContextSufficient = modelContext === 0 || fileTokens < modelContext * 0.9;

  return (
    <div className="h-full w-full bg-white text-gray-900">
      <div className="grid h-full grid-cols-2 gap-0">
        {/* 左侧：配置区 */}
        <section className="flex h-full flex-col border-r border-gray-200 bg-gray-50 p-4 overflow-y-auto">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-gray-900">📊 对话内容分析</h2>
            <p className="mt-1 text-xs text-gray-500">
              上传对话文件，使用 AI 进行智能分析
            </p>
          </div>

          {modelsError && (
            <div className="mb-2 text-xs text-red-600">{modelsError}</div>
          )}
          {!apiKey && (
            <div className="mb-2 text-xs text-amber-600">
              请先在主页填写 API Key
            </div>
          )}

          {/* 文件上传区 */}
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              📁 上传对话文件
            </label>
            <div
              className={`relative flex min-h-24 cursor-pointer items-center justify-center rounded-lg border-2 border-dashed transition-colors ${
                fileContent
                  ? "border-gray-300 bg-white"
                  : "border-gray-300 bg-gray-100 hover:border-gray-400 hover:bg-gray-50"
              }`}
              onClick={() => !fileContent && fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.csv"
                className="hidden"
                onChange={handleFileUpload}
              />
              {fileContent ? (
                <div className="w-full p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">📄</span>
                      <span className="text-sm font-medium text-gray-900">
                        {fileName}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
                      onClick={(e) => {
                        e.stopPropagation();
                        clearFile();
                      }}
                      title="清除文件"
                    >
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>{fileContent.length.toLocaleString()} 字符</span>
                    <span>预估 {formatTokens(fileTokens)} tokens</span>
                  </div>
                </div>
              ) : (
                <div className="text-center">
                  <div className="mb-1 text-2xl">📤</div>
                  <div className="text-sm text-gray-500">
                    拖拽或点击上传 .txt 或 .csv 文件
                  </div>
                </div>
              )}
            </div>
            {fileError && (
              <div className="mt-1 text-xs text-red-600">{fileError}</div>
            )}
          </div>

          {/* 文件内容预览 */}
          {fileContent && (
            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium text-gray-700">
                📄 文件内容预览
              </label>
              <div className="max-h-40 overflow-y-auto rounded-lg border border-gray-200 bg-white p-3">
                <pre className="whitespace-pre-wrap text-xs text-gray-600">
                  {fileContent.slice(0, 2000)}
                  {fileContent.length > 2000 && (
                    <span className="text-gray-400">
                      {"\n\n"}... 省略 {(fileContent.length - 2000).toLocaleString()} 字符 ...
                    </span>
                  )}
                </pre>
              </div>
            </div>
          )}

          {/* 模型选择 */}
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              🤖 选择模型
            </label>
            <div className="flex gap-2">
              <select
                className={`min-w-0 flex-1 rounded-lg border bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:ring-1 ${
                  !isContextSufficient
                    ? "border-amber-400 focus:border-amber-500 focus:ring-amber-500"
                    : "border-gray-300 focus:border-gray-900 focus:ring-gray-900"
                }`}
                value={selectedModelId}
                onChange={(e) => setSelectedModelId(e.target.value)}
                disabled={models.length === 0}
              >
                {models.length === 0 ? (
                  <option value="">点击刷新加载模型</option>
                ) : null}
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id}
                    {m.context_length
                      ? ` (${formatContextLength(m.context_length)})`
                      : ""}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="flex-shrink-0 rounded-lg border border-gray-300 bg-white px-2.5 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
                onClick={loadModels}
                disabled={modelsLoading || !apiKey}
                title="刷新模型列表"
              >
                <svg
                  className={`h-4 w-4 ${modelsLoading ? "animate-spin" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
            </div>
            {!isContextSufficient && (
              <div className="mt-1 text-xs text-amber-600">
                ⚠️ 文件内容可能超出模型上下文限制，建议选择更大上下文的模型
              </div>
            )}
          </div>

          {/* 预设提示词选择 */}
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              🎯 分析类型
            </label>
            <div className="flex flex-wrap gap-2">
              {PRESET_PROMPTS.map((preset) => (
                <button
                  key={preset.name}
                  type="button"
                  className={`rounded-full px-3 py-1 text-xs transition-colors ${
                    analysisPrompt === preset.prompt
                      ? "bg-gray-900 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                  }`}
                  onClick={() => applyPreset(preset.prompt)}
                >
                  {preset.name}
                </button>
              ))}
            </div>
          </div>

          {/* 提示词编辑 */}
          <div className="mb-4 flex-1">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              📝 分析提示词
            </label>
            <textarea
              className="h-40 w-full resize-y rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none placeholder:text-gray-400 focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
              value={analysisPrompt}
              onChange={(e) => setAnalysisPrompt(e.target.value)}
              placeholder="输入分析指令..."
            />
          </div>

          {/* 分析按钮 */}
          <div>
            <button
              type="button"
              className="w-full rounded-lg bg-gray-900 px-6 py-3 text-sm font-medium text-white shadow-lg hover:bg-gray-800 disabled:opacity-50"
              onClick={handleAnalyze}
              disabled={analyzing || !fileContent.trim() || !selectedModelId}
            >
              {analyzing ? "分析中..." : "🔍 开始分析（Cmd+Enter）"}
            </button>
          </div>
        </section>

        {/* 右侧：结果区 */}
        <section className="flex h-full flex-col bg-white p-4 overflow-y-auto">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-700">📋 分析结果</h3>
            {analysisResult && (
              <button
                type="button"
                className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
                onClick={copyResult}
              >
                复制结果
              </button>
            )}
          </div>

          <div className="flex-1 rounded-lg border border-gray-200 bg-gray-50 p-4">
            {analyzing ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <div className="mb-2 text-2xl">⏳</div>
                  <div className="text-sm text-gray-500">正在分析中...</div>
                </div>
              </div>
            ) : analysisError ? (
              <div className="text-sm text-red-600">{analysisError}</div>
            ) : analysisResult ? (
              <div className="whitespace-pre-wrap text-sm text-gray-900">
                {analysisResult}
              </div>
            ) : (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <div className="mb-2 text-4xl opacity-30">📊</div>
                  <div className="text-sm text-gray-400">
                    上传文件并点击分析，结果将显示在这里
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

