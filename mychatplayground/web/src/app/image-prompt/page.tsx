"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  createOpenRouterChatCompletion,
  createImageGeneration,
  fetchOpenRouterModels,
  IMAGE_GEN_MODELS,
  getSupportedSizesForModel,
  getDefaultSizeForModel,
  type OpenRouterModel,
  type ImageSize,
} from "@/lib/openrouter";
import { useLocalStorageState } from "@/lib/useLocalStorageState";

const LS_API_KEY = "mychatplayground.openrouter.apiKey";
const LS_BRANCH_A = "mychatplayground.imagePrompt.branchA";
const LS_BRANCH_B = "mychatplayground.imagePrompt.branchB";
const LS_BRANCH_A_NAME = "mychatplayground.imagePrompt.branchAName";
const LS_BRANCH_B_NAME = "mychatplayground.imagePrompt.branchBName";
const LS_AUTO_GEN_IMAGE = "mychatplayground.imagePrompt.autoGenImage";

// 默认系统提示词
const DEFAULT_SYSTEM_PROMPT = `You are an expert prompt engineer specializing in AI image generation (Stable Diffusion, Midjourney, DALL-E, etc.).

Your task: Convert the user's description into an optimized English prompt for AI image generation.

Rules:
1. Output ONLY the final prompt, no explanations
2. Use descriptive tags and keywords commonly used in AI art
3. Include style modifiers (e.g., "cinematic lighting", "8k", "detailed", "masterpiece")
4. Add quality boosters appropriate for the content
5. Structure: subject + details + environment + style + quality tags
6. Keep it concise but comprehensive (usually 50-150 words)
7. If the input is in Chinese, translate and enhance it

Example output format:
"a young woman with long black hair, wearing a red kimono, standing in a traditional Japanese garden, cherry blossoms falling, golden hour lighting, highly detailed, 8k resolution, trending on artstation, digital painting, by greg rutkowski"`;

type BranchConfig = {
  modelId: string;
  systemPrompt: string;
  imageGenModelId: string; // 生图模型 ID
  imageSize: ImageSize; // 图片尺寸
};

const DEFAULT_BRANCH: BranchConfig = {
  modelId: "",
  systemPrompt: DEFAULT_SYSTEM_PROMPT,
  imageGenModelId: IMAGE_GEN_MODELS[0].id,
  imageSize: getDefaultSizeForModel(IMAGE_GEN_MODELS[0].id),
};

type BranchState = {
  loading: boolean;
  result: string;
  error: string | null;
  // 生图状态
  imageLoading: boolean;
  imageUrl: string | null;
  imageError: string | null;
};

export default function ImagePromptPage() {
  const [apiKey] = useLocalStorageState<string>(LS_API_KEY, "");
  const [branchA, setBranchA] = useLocalStorageState<BranchConfig>(
    LS_BRANCH_A,
    DEFAULT_BRANCH
  );
  const [branchB, setBranchB] = useLocalStorageState<BranchConfig>(
    LS_BRANCH_B,
    DEFAULT_BRANCH
  );

  // 分支名称
  const [branchAName, setBranchAName] = useLocalStorageState<string>(LS_BRANCH_A_NAME, "分支 A");
  const [branchBName, setBranchBName] = useLocalStorageState<string>(LS_BRANCH_B_NAME, "分支 B");
  const [editingA, setEditingA] = useState(false);
  const [editingB, setEditingB] = useState(false);
  const [tempNameA, setTempNameA] = useState("");
  const [tempNameB, setTempNameB] = useState("");

  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  const [userInput, setUserInput] = useState("");

  const [stateA, setStateA] = useState<BranchState>({
    loading: false,
    result: "",
    error: null,
    imageLoading: false,
    imageUrl: null,
    imageError: null,
  });
  const [stateB, setStateB] = useState<BranchState>({
    loading: false,
    result: "",
    error: null,
    imageLoading: false,
    imageUrl: null,
    imageError: null,
  });

  // 自动生图开关
  const [autoGenImage, setAutoGenImage] = useLocalStorageState<boolean>(LS_AUTO_GEN_IMAGE, false);

  // 图片预览弹窗
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  // 翻译状态
  const [translatingA, setTranslatingA] = useState(false);
  const [translatingB, setTranslatingB] = useState(false);
  const [translationA, setTranslationA] = useState("");
  const [translationB, setTranslationB] = useState("");

  const prevApiKeyRef = useRef<string>("");

  const loadModels = async () => {
    if (!apiKey) return;
    setModelsLoading(true);
    setModelsError(null);
    try {
      const data = await fetchOpenRouterModels(apiKey);
      setModels(data);
      // 如果分支没有选择模型，默认选第一个
      if (!branchA.modelId && data.length > 0) {
        setBranchA({ ...branchA, modelId: data[0]!.id });
      }
      if (!branchB.modelId && data.length > 0) {
        setBranchB({ ...branchB, modelId: data[0]!.id });
      }
    } catch (e) {
      setModelsError(e instanceof Error ? e.message : String(e));
    } finally {
      setModelsLoading(false);
    }
  };

  useEffect(() => {
    const prev = prevApiKeyRef.current;
    prevApiKeyRef.current = apiKey;
    if (!prev && apiKey) {
      void loadModels();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey]);

  // 生成图片函数
  const generateImageForBranch = useCallback(async (
    prompt: string,
    imageGenModelId: string,
    imageSize: ImageSize,
    setState: React.Dispatch<React.SetStateAction<BranchState>>
  ) => {
    if (!prompt.trim()) return;
    if (!apiKey.trim()) {
      setState(prev => ({ ...prev, imageLoading: false, imageUrl: null, imageError: "请先在主页填写 API Key" }));
      return;
    }
    if (!imageGenModelId) {
      setState(prev => ({ ...prev, imageLoading: false, imageUrl: null, imageError: "请先选择生图模型" }));
      return;
    }

    setState(prev => ({ ...prev, imageLoading: true, imageUrl: null, imageError: null }));

    try {
      const result = await createImageGeneration({
        apiKey: apiKey.trim(),
        request: {
          model: imageGenModelId,
          prompt: prompt,
          size: imageSize,
        },
        siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground-image-prompt",
      });

      setState(prev => ({ ...prev, imageLoading: false, imageUrl: result.imageUrl, imageError: null }));
    } catch (e) {
      setState(prev => ({
        ...prev,
        imageLoading: false,
        imageUrl: null,
        imageError: e instanceof Error ? e.message : String(e),
      }));
    }
  }, [apiKey]);

  const generateForBranch = async (
    branch: BranchConfig,
    setState: React.Dispatch<React.SetStateAction<BranchState>>,
    shouldAutoGenImage: boolean
  ) => {
    if (!userInput.trim()) return;
    if (!apiKey.trim()) {
      setState({ loading: false, result: "", error: "请先在主页填写 API Key", imageLoading: false, imageUrl: null, imageError: null });
      return;
    }
    if (!branch.modelId) {
      setState({ loading: false, result: "", error: "请先选择模型", imageLoading: false, imageUrl: null, imageError: null });
      return;
    }

    setState({ loading: true, result: "", error: null, imageLoading: false, imageUrl: null, imageError: null });

    try {
      const resp = await createOpenRouterChatCompletion({
        apiKey: apiKey.trim(),
        request: {
          model: branch.modelId,
          messages: [
            { role: "system", content: branch.systemPrompt },
            { role: "user", content: userInput.trim() },
          ],
          temperature: 0.7,
          max_tokens: 500,
        },
        siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground-image-prompt",
      });

      const content = resp.choices?.[0]?.message?.content;
      const output = typeof content === "string" ? content.trim() : "";
      setState(prev => ({ ...prev, loading: false, result: output, error: null }));

      // 如果启用自动生图，则自动调用生图
      if (shouldAutoGenImage && output && branch.imageGenModelId) {
        void generateImageForBranch(output, branch.imageGenModelId, branch.imageSize, setState);
      }
    } catch (e) {
      setState(prev => ({
        ...prev,
        loading: false,
        result: "",
        error: e instanceof Error ? e.message : String(e),
      }));
    }
  };

  const handleGenerate = () => {
    // 清空之前的翻译结果
    setTranslationA("");
    setTranslationB("");
    // 同时发起两个分支的请求
    void generateForBranch(branchA, setStateA, autoGenImage);
    void generateForBranch(branchB, setStateB, autoGenImage);
  };

  // 手动生成图片
  const handleGenerateImageA = () => {
    if (stateA.result) {
      void generateImageForBranch(stateA.result, branchA.imageGenModelId, branchA.imageSize, setStateA);
    }
  };

  const handleGenerateImageB = () => {
    if (stateB.result) {
      void generateImageForBranch(stateB.result, branchB.imageGenModelId, branchB.imageSize, setStateB);
    }
  };

  // 下载图片
  const downloadImage = async (imageUrl: string, filename: string) => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch {
      // 如果是 base64，直接下载
      const a = document.createElement("a");
      a.href = imageUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // ignore
    }
  };

  // 检测是否有英文
  const hasEnglish = (text: string): boolean => {
    return /[a-zA-Z]{2,}/.test(text);
  };

  // 翻译函数
  const translateResult = async (
    content: string,
    modelId: string,
    setTranslating: (v: boolean) => void,
    setTranslation: (v: string) => void
  ) => {
    if (!hasEnglish(content)) {
      return;
    }
    if (!apiKey.trim()) {
      return;
    }
    if (!modelId) {
      return;
    }

    setTranslating(true);
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
        appName: "mychatplayground-image-prompt",
      });
      const respContent = resp.choices?.[0]?.message?.content;
      const translated = typeof respContent === "string" ? respContent.trim() : "";
      if (translated) {
        setTranslation(translated);
      }
    } catch {
      // ignore
    } finally {
      setTranslating(false);
    }
  };

  const isGenerating = stateA.loading || stateB.loading;

  return (
    <div className="h-full w-full bg-white text-gray-900">
      <div className="grid h-full grid-cols-12 gap-0">
        {/* 左侧：输入区 */}
        <section className="col-span-3 flex h-full flex-col border-r border-gray-200 bg-gray-50 p-4">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-gray-900">✨ 文生图提示词生成</h2>
            <p className="mt-1 text-xs text-gray-500">
              优化生图提示词，以适用不同渠道的生图模型
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

          {/* 自动生图开关 */}
          <div className="mb-4 flex items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2">
            <div>
              <div className="text-sm font-medium text-gray-900">自动生图</div>
              <div className="text-xs text-gray-500">生成提示词后自动调用生图模型</div>
            </div>
            <button
              type="button"
              onClick={() => setAutoGenImage(!autoGenImage)}
              className={`relative h-6 w-11 rounded-full transition-colors ${
                autoGenImage ? "bg-gray-900" : "bg-gray-300"
              }`}
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                  autoGenImage ? "translate-x-5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>

          {/* 生成按钮 */}
          <div className="mb-4">
            <button
              type="button"
              className="w-full rounded-lg bg-gray-900 px-6 py-3 text-sm font-medium text-white shadow-lg hover:bg-gray-800 disabled:opacity-50"
              onClick={handleGenerate}
              disabled={isGenerating || !userInput.trim()}
            >
              {isGenerating ? "生成中..." : autoGenImage ? "🎨 生成提示词 + 图片" : "🎨 生成提示词（Cmd+Enter）"}
            </button>
          </div>

          {/* 输入框 */}
          <div className="flex-1">
            <label>
              <div className="mb-2 text-sm font-medium text-gray-700">📝 输入描述</div>
              <textarea
                className="min-h-48 w-full resize-y rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none placeholder:text-gray-400 focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
                placeholder="例如：一个穿着白色连衣裙的女孩，站在向日葵花田里，阳光明媚，宫崎骏风格"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    if (!isGenerating) handleGenerate();
                  }
                }}
              />
            </label>
          </div>
        </section>

        {/* 分支 A */}
        <section className="col-span-4 flex h-full flex-col border-r border-gray-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2">
            <div className="rounded-full bg-gray-900 px-2 py-0.5 text-xs font-medium text-white">
              A
            </div>
            {editingA ? (
              <input
                type="text"
                className="rounded border border-gray-300 px-2 py-0.5 text-sm font-medium text-gray-900 outline-none focus:border-gray-900"
                value={tempNameA}
                onChange={(e) => setTempNameA(e.target.value)}
                onBlur={() => {
                  if (tempNameA.trim()) {
                    setBranchAName(tempNameA.trim());
                  }
                  setEditingA(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    if (tempNameA.trim()) {
                      setBranchAName(tempNameA.trim());
                    }
                    setEditingA(false);
                  } else if (e.key === "Escape") {
                    setEditingA(false);
                  }
                }}
                autoFocus
              />
            ) : (
              <h3
                className="cursor-pointer text-sm font-medium text-gray-900 hover:text-gray-600"
                onClick={() => {
                  setTempNameA(branchAName);
                  setEditingA(true);
                }}
                title="点击修改名称"
              >
                {branchAName}
              </h3>
            )}
          </div>

          {/* 模型选择 */}
          <div className="mb-3">
            <label className="text-xs text-gray-500">模型</label>
            <div className="mt-1 flex gap-2">
              <select
                className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
                value={branchA.modelId}
                onChange={(e) => setBranchA({ ...branchA, modelId: e.target.value })}
                disabled={models.length === 0}
              >
                {models.length === 0 ? (
                  <option value="">点击刷新加载模型</option>
                ) : null}
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id}
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
          </div>

          {/* 系统提示词 */}
          <div className="mb-3 flex-1">
            <label className="text-xs text-gray-500">系统提示词</label>
            <textarea
              className="mt-1 h-32 w-full resize-y rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs text-gray-900 outline-none placeholder:text-gray-400 focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
              value={branchA.systemPrompt}
              onChange={(e) =>
                setBranchA({ ...branchA, systemPrompt: e.target.value })
              }
            />
          </div>

          {/* 输出结果 */}
          <div className="mb-3">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs text-gray-500">输出结果</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:hover:bg-transparent"
                  onClick={() => translateResult(stateA.result, branchA.modelId, setTranslatingA, setTranslationA)}
                  disabled={!stateA.result || translatingA || !hasEnglish(stateA.result)}
                  title="翻译为中文"
                >
                  {translatingA ? "翻译中..." : "翻译"}
                </button>
                <button
                  type="button"
                  className="rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:hover:bg-transparent"
                  onClick={() => copyToClipboard(stateA.result)}
                  disabled={!stateA.result}
                >
                  复制
                </button>
              </div>
            </div>
            <div className="max-h-32 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-3">
              {stateA.loading ? (
                <div className="text-sm text-gray-500">生成中...</div>
              ) : stateA.error ? (
                <div className="text-sm text-red-600">{stateA.error}</div>
              ) : stateA.result ? (
                <div className="space-y-3">
                  <div className="whitespace-pre-wrap font-mono text-sm text-gray-900">
                    {stateA.result}
                  </div>
                  {translationA && (
                    <div className="border-t border-gray-200 pt-3">
                      <div className="mb-1 text-xs text-gray-400">中文翻译</div>
                      <div className="whitespace-pre-wrap text-sm text-gray-600">
                        {translationA}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-gray-400">等待生成...</div>
              )}
            </div>
          </div>

          {/* 生图模块 */}
          <div className="flex-1">
            <div className="mb-2 flex items-center gap-2 border-t border-gray-200 pt-3">
              <span className="text-xs font-medium text-gray-700">🖼️ 图片生成</span>
            </div>

            {/* 生图模型选择 */}
            <div className="mb-2">
              <label className="text-xs text-gray-500">生图模型</label>
              <select
                className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
                value={branchA.imageGenModelId}
                onChange={(e) => {
                  const newModelId = e.target.value;
                  const supportedSizes = getSupportedSizesForModel(newModelId);
                  // 如果当前尺寸不支持，切换到默认尺寸
                  const newSize = supportedSizes.includes(branchA.imageSize)
                    ? branchA.imageSize
                    : getDefaultSizeForModel(newModelId);
                  setBranchA({ ...branchA, imageGenModelId: newModelId, imageSize: newSize });
                }}
              >
                {IMAGE_GEN_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* 图片尺寸选择 */}
            <div className="mb-2">
              <label className="text-xs text-gray-500">图片尺寸（纵向）</label>
              <select
                className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
                value={branchA.imageSize}
                onChange={(e) => setBranchA({ ...branchA, imageSize: e.target.value as ImageSize })}
              >
                {getSupportedSizesForModel(branchA.imageGenModelId).map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>

            {/* 生成图片按钮 */}
            <button
              type="button"
              className="mb-2 w-full rounded-lg border border-gray-900 bg-white px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-100 disabled:opacity-50"
              onClick={handleGenerateImageA}
              disabled={!stateA.result || stateA.imageLoading}
            >
              {stateA.imageLoading ? "生成图片中..." : "🎨 生成图片"}
            </button>

            {/* 图片展示区 */}
            <div className="min-h-40 rounded-lg border border-gray-200 bg-gray-50 p-3">
              {stateA.imageLoading ? (
                <div className="flex h-32 items-center justify-center">
                  <div className="text-sm text-gray-500">图片生成中...</div>
                </div>
              ) : stateA.imageError ? (
                <div className="max-h-64 overflow-y-auto whitespace-pre-wrap break-all rounded bg-red-50 p-2 text-xs text-red-600">
                  {stateA.imageError}
                </div>
              ) : stateA.imageUrl ? (
                <div className="space-y-2">
                  <img
                    src={stateA.imageUrl}
                    alt="Generated"
                    className="max-h-48 w-full cursor-pointer rounded-lg object-contain"
                    onClick={() => setPreviewImage(stateA.imageUrl)}
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
                      onClick={() => setPreviewImage(stateA.imageUrl)}
                    >
                      放大
                    </button>
                    <button
                      type="button"
                      className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
                      onClick={() => downloadImage(stateA.imageUrl!, `image-a-${Date.now()}.png`)}
                    >
                      下载
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex h-32 items-center justify-center text-sm text-gray-400">
                  等待生成图片...
                </div>
              )}
            </div>
          </div>
        </section>

        {/* 分支 B */}
        <section className="col-span-5 flex h-full flex-col bg-white p-4">
          <div className="mb-3 flex items-center gap-2">
            <div className="rounded-full bg-gray-500 px-2 py-0.5 text-xs font-medium text-white">
              B
            </div>
            {editingB ? (
              <input
                type="text"
                className="rounded border border-gray-300 px-2 py-0.5 text-sm font-medium text-gray-900 outline-none focus:border-gray-900"
                value={tempNameB}
                onChange={(e) => setTempNameB(e.target.value)}
                onBlur={() => {
                  if (tempNameB.trim()) {
                    setBranchBName(tempNameB.trim());
                  }
                  setEditingB(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    if (tempNameB.trim()) {
                      setBranchBName(tempNameB.trim());
                    }
                    setEditingB(false);
                  } else if (e.key === "Escape") {
                    setEditingB(false);
                  }
                }}
                autoFocus
              />
            ) : (
              <h3
                className="cursor-pointer text-sm font-medium text-gray-900 hover:text-gray-600"
                onClick={() => {
                  setTempNameB(branchBName);
                  setEditingB(true);
                }}
                title="点击修改名称"
              >
                {branchBName}
              </h3>
            )}
          </div>

          {/* 模型选择 */}
          <div className="mb-3">
            <label className="text-xs text-gray-500">模型</label>
            <div className="mt-1 flex gap-2">
              <select
                className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
                value={branchB.modelId}
                onChange={(e) => setBranchB({ ...branchB, modelId: e.target.value })}
                disabled={models.length === 0}
              >
                {models.length === 0 ? (
                  <option value="">点击刷新加载模型</option>
                ) : null}
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id}
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
          </div>

          {/* 系统提示词 */}
          <div className="mb-3 flex-1">
            <label className="text-xs text-gray-500">系统提示词</label>
            <textarea
              className="mt-1 h-32 w-full resize-y rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs text-gray-900 outline-none placeholder:text-gray-400 focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
              value={branchB.systemPrompt}
              onChange={(e) =>
                setBranchB({ ...branchB, systemPrompt: e.target.value })
              }
            />
          </div>

          {/* 输出结果 */}
          <div className="mb-3">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs text-gray-500">输出结果</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:hover:bg-transparent"
                  onClick={() => translateResult(stateB.result, branchB.modelId, setTranslatingB, setTranslationB)}
                  disabled={!stateB.result || translatingB || !hasEnglish(stateB.result)}
                  title="翻译为中文"
                >
                  {translatingB ? "翻译中..." : "翻译"}
                </button>
                <button
                  type="button"
                  className="rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:hover:bg-transparent"
                  onClick={() => copyToClipboard(stateB.result)}
                  disabled={!stateB.result}
                >
                  复制
                </button>
              </div>
            </div>
            <div className="max-h-32 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-3">
              {stateB.loading ? (
                <div className="text-sm text-gray-500">生成中...</div>
              ) : stateB.error ? (
                <div className="text-sm text-red-600">{stateB.error}</div>
              ) : stateB.result ? (
                <div className="space-y-3">
                  <div className="whitespace-pre-wrap font-mono text-sm text-gray-900">
                    {stateB.result}
                  </div>
                  {translationB && (
                    <div className="border-t border-gray-200 pt-3">
                      <div className="mb-1 text-xs text-gray-400">中文翻译</div>
                      <div className="whitespace-pre-wrap text-sm text-gray-600">
                        {translationB}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-gray-400">等待生成...</div>
              )}
            </div>
          </div>

          {/* 生图模块 */}
          <div className="flex-1">
            <div className="mb-2 flex items-center gap-2 border-t border-gray-200 pt-3">
              <span className="text-xs font-medium text-gray-700">🖼️ 图片生成</span>
            </div>

            {/* 生图模型选择 */}
            <div className="mb-2">
              <label className="text-xs text-gray-500">生图模型</label>
              <select
                className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
                value={branchB.imageGenModelId}
                onChange={(e) => {
                  const newModelId = e.target.value;
                  const supportedSizes = getSupportedSizesForModel(newModelId);
                  // 如果当前尺寸不支持，切换到默认尺寸
                  const newSize = supportedSizes.includes(branchB.imageSize)
                    ? branchB.imageSize
                    : getDefaultSizeForModel(newModelId);
                  setBranchB({ ...branchB, imageGenModelId: newModelId, imageSize: newSize });
                }}
              >
                {IMAGE_GEN_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* 图片尺寸选择 */}
            <div className="mb-2">
              <label className="text-xs text-gray-500">图片尺寸（纵向）</label>
              <select
                className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
                value={branchB.imageSize}
                onChange={(e) => setBranchB({ ...branchB, imageSize: e.target.value as ImageSize })}
              >
                {getSupportedSizesForModel(branchB.imageGenModelId).map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>

            {/* 生成图片按钮 */}
            <button
              type="button"
              className="mb-2 w-full rounded-lg border border-gray-900 bg-white px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-100 disabled:opacity-50"
              onClick={handleGenerateImageB}
              disabled={!stateB.result || stateB.imageLoading}
            >
              {stateB.imageLoading ? "生成图片中..." : "🎨 生成图片"}
            </button>

            {/* 图片展示区 */}
            <div className="min-h-40 rounded-lg border border-gray-200 bg-gray-50 p-3">
              {stateB.imageLoading ? (
                <div className="flex h-32 items-center justify-center">
                  <div className="text-sm text-gray-500">图片生成中...</div>
                </div>
              ) : stateB.imageError ? (
                <div className="max-h-64 overflow-y-auto whitespace-pre-wrap break-all rounded bg-red-50 p-2 text-xs text-red-600">
                  {stateB.imageError}
                </div>
              ) : stateB.imageUrl ? (
                <div className="space-y-2">
                  <img
                    src={stateB.imageUrl}
                    alt="Generated"
                    className="max-h-48 w-full cursor-pointer rounded-lg object-contain"
                    onClick={() => setPreviewImage(stateB.imageUrl)}
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
                      onClick={() => setPreviewImage(stateB.imageUrl)}
                    >
                      放大
                    </button>
                    <button
                      type="button"
                      className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
                      onClick={() => downloadImage(stateB.imageUrl!, `image-b-${Date.now()}.png`)}
                    >
                      下载
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex h-32 items-center justify-center text-sm text-gray-400">
                  等待生成图片...
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* 图片预览弹窗 */}
      {previewImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
          onClick={() => setPreviewImage(null)}
        >
          <div className="relative max-h-[90vh] max-w-[90vw]">
            <img
              src={previewImage}
              alt="Preview"
              className="max-h-[90vh] max-w-[90vw] rounded-lg object-contain"
            />
            <button
              type="button"
              className="absolute -right-3 -top-3 rounded-full bg-white p-2 shadow-lg hover:bg-gray-100"
              onClick={() => setPreviewImage(null)}
            >
              <svg className="h-5 w-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

