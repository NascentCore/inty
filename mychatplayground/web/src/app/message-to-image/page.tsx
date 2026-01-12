"use client";

import { useEffect, useRef, useState, useCallback, ChangeEvent } from "react";
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
import {
  createFalImageGeneration,
  FAL_IMAGE_MODELS,
  FAL_IMAGE_SIZES,
  type FalImageSize,
} from "@/lib/fal";
import { useLocalStorageState } from "@/lib/useLocalStorageState";

const LS_API_KEY = "mychatplayground.openrouter.apiKey";
const LS_FAL_API_KEY = "mychatplayground.fal.apiKey";
const LS_MSG_TO_IMG_MODEL = "mychatplayground.messageToImage.model";
const LS_MSG_TO_IMG_SAVED_INSTRUCTION = "mychatplayground.messageToImage.savedInstruction";
const LS_MSG_TO_IMG_IMAGE_MODEL = "mychatplayground.messageToImage.imageModel";
const LS_MSG_TO_IMG_IMAGE_SIZE = "mychatplayground.messageToImage.imageSize";
const LS_MSG_TO_IMG_VARIABLES = "mychatplayground.messageToImage.variables";
const LS_MSG_TO_IMG_IMAGE_PROVIDER = "mychatplayground.messageToImage.imageProvider";
const LS_MSG_TO_IMG_FAL_MODEL = "mychatplayground.messageToImage.falModel";
const LS_MSG_TO_IMG_FAL_SIZE = "mychatplayground.messageToImage.falSize";

// 图生图提供商类型
type ImageProvider = "openrouter" | "fal";

// 固定的生图提示词前缀（用于强调参考图特征）
const FIXED_PROMPT_PREFIX = "The facial features, hairstyle, and body shape of the female figure in the reference image must be followed.";

// 变量类型
type Variable = {
  id: string;
  name: string; // 变量名，如 chat_history
  value: string; // 变量值
};

// 默认变量
const DEFAULT_VARIABLES: Variable[] = [
  { id: "1", name: "chat_history", value: "" },
  { id: "2", name: "user_info", value: "" },
];

// 默认 LLM 指令：使用变量引用
const DEFAULT_LLM_INSTRUCTION = `你是一个专业的 AI 图像生成提示词专家。你的任务是处理用户提供的各类信息，并转换为高质量的英文图像生成提示词。

【聊天记录】
{chat_history}

【角色信息】
{user_info}

【处理要求】
1. 综合分析上述所有信息
2. 提取关键的视觉元素（人物外貌、动作、表情、场景、氛围等）
3. 将信息整合为连贯的画面描述

【输出要求】
1. 只输出最终的英文提示词，不要添加任何解释
2. 使用 AI 绘画常用的描述性标签和关键词
3. 包含风格修饰词（如 "cinematic lighting"、"8k"、"detailed"、"masterpiece"）
4. 添加适当的质量提升词
5. 结构：主体 + 细节 + 环境 + 风格 + 质量标签
6. 保持简洁但全面（通常 50-150 词）
7. 如果提供了角色参考图，请在描述中融入角色的视觉特征

【示例输出】
"a young woman with long flowing silver hair, wearing an elegant black dress, sitting by a rain-streaked window, melancholic expression, soft ambient lighting from outside, atmospheric mood, highly detailed, 8k resolution, digital art, cinematic composition, by artgerm and greg rutkowski"`;

export default function MessageToImagePage() {
  const [apiKey] = useLocalStorageState<string>(LS_API_KEY, "");
  const [falApiKey, setFalApiKey] = useLocalStorageState<string>(LS_FAL_API_KEY, "");
  const [modelId, setModelId] = useLocalStorageState<string>(LS_MSG_TO_IMG_MODEL, "");
  
  // 图生图提供商选择
  const [imageProvider, setImageProvider] = useLocalStorageState<ImageProvider>(
    LS_MSG_TO_IMG_IMAGE_PROVIDER,
    "openrouter"
  );
  
  // fal.ai 模型和尺寸
  const [falModelId, setFalModelId] = useLocalStorageState<string>(
    LS_MSG_TO_IMG_FAL_MODEL,
    FAL_IMAGE_MODELS[0].id
  );
  const [falImageSize, setFalImageSize] = useLocalStorageState<FalImageSize>(
    LS_MSG_TO_IMG_FAL_SIZE,
    "portrait_4_3"
  );
  
  // LLM 指令：保存版本存储在 localStorage，当前编辑版本是临时状态
  const [savedInstruction, setSavedInstruction] = useLocalStorageState<string>(
    LS_MSG_TO_IMG_SAVED_INSTRUCTION,
    DEFAULT_LLM_INSTRUCTION
  );
  const [llmInstruction, setLlmInstruction] = useState<string>(savedInstruction);
  
  // 检测指令是否有未保存的更改
  const hasUnsavedChanges = llmInstruction !== savedInstruction;
  
  // 保存指令
  const saveInstruction = () => {
    setSavedInstruction(llmInstruction);
  };
  
  // 当编辑指令时
  const handleInstructionChange = (value: string) => {
    setLlmInstruction(value);
  };
  
  const [imageGenModelId, setImageGenModelId] = useLocalStorageState<string>(
    LS_MSG_TO_IMG_IMAGE_MODEL,
    IMAGE_GEN_MODELS[0].id
  );
  const [imageSize, setImageSize] = useLocalStorageState<ImageSize>(
    LS_MSG_TO_IMG_IMAGE_SIZE,
    getDefaultSizeForModel(IMAGE_GEN_MODELS[0].id)
  );

  // 变量管理
  const [variables, setVariables] = useLocalStorageState<Variable[]>(
    LS_MSG_TO_IMG_VARIABLES,
    DEFAULT_VARIABLES
  );
  const [editingVarId, setEditingVarId] = useState<string | null>(null);
  const [tempVarName, setTempVarName] = useState("");

  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  // 角色参考图
  const [referenceImage, setReferenceImage] = useState<string | null>(null);
  const [referenceImageName, setReferenceImageName] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 提示词生成状态
  const [promptLoading, setPromptLoading] = useState(false);
  const [generatedPrompt, setGeneratedPrompt] = useState("");
  const [promptError, setPromptError] = useState<string | null>(null);

  // 翻译状态
  const [translating, setTranslating] = useState(false);
  const [translation, setTranslation] = useState("");

  // 图片生成状态
  const [imageLoading, setImageLoading] = useState(false);
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [imageGenerationTime, setImageGenerationTime] = useState<number | null>(null); // 生成耗时（毫秒）

  // 图片预览弹窗
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const prevApiKeyRef = useRef<string>("");

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

  // 处理图片上传
  const handleImageUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert("请上传图片文件");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert("图片大小不能超过 10MB");
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const result = event.target?.result;
      if (typeof result === "string") {
        setReferenceImage(result);
        setReferenceImageName(file.name);
      }
    };
    reader.readAsDataURL(file);
  };

  // 清除参考图
  const clearReferenceImage = () => {
    setReferenceImage(null);
    setReferenceImageName("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // 更新变量值
  const updateVariableValue = (id: string, value: string) => {
    setVariables(variables.map((v) => (v.id === id ? { ...v, value } : v)));
  };

  // 更新变量名
  const updateVariableName = (id: string, name: string) => {
    // 移除特殊字符，只保留字母、数字、下划线
    const cleanName = name.replace(/[^a-zA-Z0-9_]/g, "");
    setVariables(variables.map((v) => (v.id === id ? { ...v, name: cleanName } : v)));
  };

  // 添加新变量
  const addVariable = () => {
    const newId = Date.now().toString();
    setVariables([...variables, { id: newId, name: `var_${variables.length + 1}`, value: "" }]);
  };

  // 删除变量
  const deleteVariable = (id: string) => {
    if (variables.length <= 1) return; // 至少保留一个变量
    setVariables(variables.filter((v) => v.id !== id));
  };

  // 将变量替换到 LLM 指令中
  const replaceVariablesInInstruction = (instruction: string): string => {
    let result = instruction;
    for (const variable of variables) {
      const pattern = new RegExp(`\\{${variable.name}\\}`, "g");
      result = result.replace(pattern, variable.value || `[${variable.name} 未填写]`);
    }
    return result;
  };

  // 检查是否有变量内容
  const hasVariableContent = variables.some((v) => v.value.trim());

  // 生成提示词
  const generatePrompt = async () => {
    if (!hasVariableContent) return;
    if (!apiKey.trim()) {
      setPromptError("请先在主页填写 API Key");
      return;
    }
    if (!modelId) {
      setPromptError("请先选择模型");
      return;
    }

    setPromptLoading(true);
    setGeneratedPrompt("");
    setPromptError(null);
    setGeneratedImageUrl(null);
    setImageError(null);

    try {
      // 将变量替换到 LLM 指令中
      let processedInstruction = replaceVariablesInInstruction(llmInstruction);
      
      // 如果有参考图，添加提示
      if (referenceImage) {
        processedInstruction += `\n\n【注意】用户提供了一张角色参考图，请在生成提示词时融入角色的视觉特征。`;
      }

      const messages: Array<{ role: "system" | "user" | "assistant"; content: string }> = [
        { role: "system", content: processedInstruction },
        { role: "user", content: "请根据以上信息生成生图提示词。" },
      ];

      const resp = await createOpenRouterChatCompletion({
        apiKey: apiKey.trim(),
        request: {
          model: modelId,
          messages,
          temperature: 0.7,
          max_tokens: 500,
        },
        siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground-message-to-image",
      });

      const content = resp.choices?.[0]?.message?.content;
      const output = typeof content === "string" ? content.trim() : "";
      setGeneratedPrompt(output);
      // 清空之前的翻译
      setTranslation("");
    } catch (e) {
      setPromptError(e instanceof Error ? e.message : String(e));
    } finally {
      setPromptLoading(false);
    }
  };

  // 检测是否有英文
  const hasEnglish = (text: string): boolean => {
    return /[a-zA-Z]{2,}/.test(text);
  };

  // 翻译函数
  const translatePrompt = async () => {
    if (!generatedPrompt || !hasEnglish(generatedPrompt)) {
      return;
    }
    if (!apiKey.trim() || !modelId) {
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
              content: generatedPrompt,
            },
          ],
          temperature: 0.3,
          max_tokens: 2000,
        },
        siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
        appName: "mychatplayground-message-to-image",
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

  // 生成图片
  const generateImage = useCallback(async () => {
    const basePrompt = generatedPrompt.trim();
    if (!basePrompt) return;
    
    // 拼接固定提示词到最前方（加空格分隔）
    const promptToUse = FIXED_PROMPT_PREFIX + " " + basePrompt;
    
    // 根据提供商检查 API Key
    if (imageProvider === "openrouter") {
      if (!apiKey.trim()) {
        setImageError("请先在主页填写 OpenRouter API Key");
        return;
      }
      if (!imageGenModelId) {
        setImageError("请先选择生图模型");
        return;
      }
    } else {
      if (!falApiKey.trim()) {
        setImageError("请先填写 fal.ai API Key");
        return;
      }
      if (!falModelId) {
        setImageError("请先选择 fal.ai 模型");
        return;
      }
      // 检查是否是需要参考图的模型
      const selectedModel = FAL_IMAGE_MODELS.find(m => m.id === falModelId);
      if (selectedModel && "requiresImage" in selectedModel && selectedModel.requiresImage && !referenceImage) {
        setImageError("该模型是图像编辑模型，必须上传参考图才能使用");
        return;
      }
    }

    const startTime = Date.now(); // 记录开始时间
    setImageLoading(true);
    setGeneratedImageUrl(null);
    setImageError(null);
    setImageGenerationTime(null);

    try {
      let imageUrl: string;
      
      if (imageProvider === "openrouter") {
        // 使用 OpenRouter
        const result = await createImageGeneration({
          apiKey: apiKey.trim(),
          request: {
            model: imageGenModelId,
            prompt: promptToUse,
            size: imageSize,
            referenceImage: referenceImage || undefined,
          },
          siteUrl: typeof window !== "undefined" ? window.location.origin : undefined,
          appName: "mychatplayground-message-to-image",
        });
        imageUrl = result.imageUrl;
      } else {
        // 使用 fal.ai
        const result = await createFalImageGeneration({
          apiKey: falApiKey.trim(),
          modelId: falModelId,
          request: {
            prompt: promptToUse,
            image_size: falImageSize,
            image_url: referenceImage || undefined,
            strength: referenceImage ? 0.75 : undefined,
          },
        });
        imageUrl = result.imageUrl;
      }

      const endTime = Date.now(); // 记录结束时间
      setImageGenerationTime(endTime - startTime); // 计算耗时
      setGeneratedImageUrl(imageUrl);
    } catch (e) {
      setImageError(e instanceof Error ? e.message : String(e));
    } finally {
      setImageLoading(false);
    }
  }, [apiKey, falApiKey, generatedPrompt, imageGenModelId, imageSize, referenceImage, imageProvider, falModelId, falImageSize]);

  // 复制到剪贴板
  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // ignore
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
      const a = document.createElement("a");
      a.href = imageUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  // 处理生图模型切换
  const handleImageModelChange = (newModelId: string) => {
    const supportedSizes = getSupportedSizesForModel(newModelId);
    const newSize = supportedSizes.includes(imageSize)
      ? imageSize
      : getDefaultSizeForModel(newModelId);
    setImageGenModelId(newModelId);
    setImageSize(newSize);
  };

  // 插入变量到 LLM 指令
  const insertVariableToInstruction = (varName: string) => {
    const newValue = llmInstruction + `{${varName}}`;
    handleInstructionChange(newValue);
  };

  return (
    <div className="h-full w-full bg-white text-gray-900">
      <div className="grid h-full grid-cols-12 gap-0">
        {/* 左侧：变量管理 + LLM 指令 */}
        <section className="col-span-4 flex h-full flex-col overflow-y-auto border-r border-gray-200 bg-gradient-to-b from-slate-50 to-white p-4">
          <div className="mb-4">
            <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <span className="text-2xl">🎭</span>
              消息生图测试
            </h2>
            <p className="mt-1 text-xs text-gray-500">
              适用于无多模态的 img2img 测试，通过 LLM 单独处理提示词后再生图
            </p>
          </div>

          {modelsError && (
            <div className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
              {modelsError}
            </div>
          )}
          {!apiKey && (
            <div className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-600">
              请先在主页填写 API Key
            </div>
          )}

          {/* 变量管理区域 */}
          <div className="mb-4">
            <div className="mb-2 flex items-center justify-between">
              <label className="flex items-center gap-1 text-sm font-medium text-gray-700">
                <span>📦</span>
                变量配置
              </label>
              <button
                type="button"
                className="flex items-center gap-1 rounded-lg bg-indigo-50 px-2 py-1 text-xs text-indigo-600 transition-colors hover:bg-indigo-100"
                onClick={addVariable}
              >
                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                添加变量
              </button>
            </div>

            <div className="space-y-3">
              {variables.map((variable) => (
                <div
                  key={variable.id}
                  className="rounded-xl border border-gray-200 bg-white p-3 shadow-sm"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {editingVarId === variable.id ? (
                        <input
                          type="text"
                          className="w-32 rounded border border-indigo-300 bg-indigo-50 px-2 py-0.5 font-mono text-xs text-indigo-700 outline-none"
                          value={tempVarName}
                          onChange={(e) => setTempVarName(e.target.value)}
                          onBlur={() => {
                            if (tempVarName.trim()) {
                              updateVariableName(variable.id, tempVarName);
                            }
                            setEditingVarId(null);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              if (tempVarName.trim()) {
                                updateVariableName(variable.id, tempVarName);
                              }
                              setEditingVarId(null);
                            } else if (e.key === "Escape") {
                              setEditingVarId(null);
                            }
                          }}
                          autoFocus
                        />
                      ) : (
                        <code
                          className="cursor-pointer rounded bg-indigo-50 px-2 py-0.5 font-mono text-xs text-indigo-700 hover:bg-indigo-100"
                          onClick={() => {
                            setTempVarName(variable.name);
                            setEditingVarId(variable.id);
                          }}
                          title="点击编辑变量名"
                        >
                          {`{${variable.name}}`}
                        </code>
                      )}
                      <button
                        type="button"
                        className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 hover:bg-gray-200"
                        onClick={() => insertVariableToInstruction(variable.name)}
                        title="插入到 LLM 指令"
                      >
                        插入
                      </button>
                    </div>
                    <div className="flex items-center gap-1">
                      {variable.value && (
                        <button
                          type="button"
                          className="rounded p-1 text-gray-400 hover:bg-amber-50 hover:text-amber-500"
                          onClick={() => updateVariableValue(variable.id, "")}
                          title="清空内容"
                        >
                          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M3 12l6.414 6.414a2 2 0 001.414.586H19a2 2 0 002-2V7a2 2 0 00-2-2h-8.172a2 2 0 00-1.414.586L3 12z" />
                          </svg>
                        </button>
                      )}
                      {variables.length > 1 && (
                        <button
                          type="button"
                          className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                          onClick={() => deleteVariable(variable.id)}
                          title="删除变量"
                        >
                          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                  <textarea
                    className="w-full resize-none rounded-lg border border-gray-200 bg-gray-50/50 px-3 py-2 text-xs text-gray-900 outline-none placeholder:text-gray-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    rows={3}
                    placeholder={`输入 ${variable.name} 的内容...`}
                    value={variable.value}
                    onChange={(e) => updateVariableValue(variable.id, e.target.value)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* LLM 指令窗口 */}
          <div className="mb-4 flex flex-1 flex-col">
            <div className="mb-2 flex items-center justify-between">
              <label className="flex items-center gap-1 text-sm font-medium text-gray-700">
                <span>📜</span>
                LLM 指令
                {hasUnsavedChanges && (
                  <span className="ml-1 text-[10px] text-amber-500">● 未保存</span>
                )}
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className={`rounded-lg px-2 py-1 text-xs font-medium transition-colors ${
                    hasUnsavedChanges
                      ? "bg-green-500 text-white hover:bg-green-600"
                      : "bg-gray-100 text-gray-400 cursor-not-allowed"
                  }`}
                  onClick={saveInstruction}
                  disabled={!hasUnsavedChanges}
                  title={hasUnsavedChanges ? "保存指令" : "已保存"}
                >
                  {hasUnsavedChanges ? "💾 保存" : "✓ 已保存"}
                </button>
                <button
                  type="button"
                  className="text-xs text-indigo-600 hover:text-indigo-700"
                  onClick={() => handleInstructionChange(DEFAULT_LLM_INSTRUCTION)}
                >
                  重置
                </button>
              </div>
            </div>
            <div className="mb-2 flex flex-wrap gap-1">
              {variables.map((v) => (
                <button
                  key={v.id}
                  type="button"
                  className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[10px] text-indigo-600 hover:bg-indigo-100"
                  onClick={() => insertVariableToInstruction(v.name)}
                  title={`点击插入 {${v.name}}`}
                >
                  {`{${v.name}}`}
                </button>
              ))}
            </div>
            <textarea
              className={`min-h-[150px] flex-1 w-full resize-none rounded-xl border bg-white px-3 py-2 font-mono text-xs text-gray-900 shadow-sm outline-none placeholder:text-gray-400 focus:ring-2 focus:ring-indigo-500/20 ${
                hasUnsavedChanges 
                  ? "border-amber-300 focus:border-amber-400" 
                  : "border-gray-200 focus:border-indigo-500"
              }`}
              placeholder="输入 LLM 指令，使用 {变量名} 引用变量内容..."
              value={llmInstruction}
              onChange={(e) => handleInstructionChange(e.target.value)}
            />
          </div>

          {/* 模型选择 */}
          <div className="mb-4">
            <label className="mb-2 flex items-center gap-1 text-sm font-medium text-gray-700">
              <span>🤖</span>
              提示词生成模型
            </label>
            <div className="flex gap-2">
              <select
                className="min-w-0 flex-1 rounded-lg border border-gray-200 bg-white px-2 py-2 text-xs text-gray-900 shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
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
                className="flex-shrink-0 rounded-lg border border-gray-200 bg-white px-2 py-2 text-gray-600 shadow-sm transition-colors hover:bg-gray-50 disabled:opacity-50"
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

          {/* 生成提示词按钮 */}
          <button
            type="button"
            className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/30 transition-all hover:from-indigo-700 hover:to-purple-700 hover:shadow-indigo-500/40 disabled:opacity-50 disabled:shadow-none"
            onClick={generatePrompt}
            disabled={promptLoading || !hasVariableContent}
          >
            {promptLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                处理中...
              </span>
            ) : (
              "✨ 生成提示词"
            )}
          </button>
        </section>

        {/* 中间：提示词结果 + 生图配置 */}
        <section className="col-span-4 flex h-full flex-col overflow-y-auto border-r border-gray-200 bg-gradient-to-b from-gray-50 to-white p-4">
          {/* 角色参考图上传 */}
          <div className="mb-4">
            <label className="mb-2 flex items-center gap-1 text-sm font-medium text-gray-700">
              <span>🖼️</span>
              角色参考图（可选）
            </label>
            <div className="rounded-xl border-2 border-dashed border-gray-200 bg-white p-3 transition-colors hover:border-indigo-300">
              {referenceImage ? (
                <div className="flex items-center gap-3">
                  <div className="relative flex-shrink-0">
                    <img
                      src={referenceImage}
                      alt="Reference"
                      className="h-16 w-16 cursor-pointer rounded-lg object-cover shadow-sm transition-transform hover:scale-105"
                      onClick={() => setPreviewImage(referenceImage)}
                    />
                    <button
                      type="button"
                      className="absolute -right-1.5 -top-1.5 rounded-full bg-red-500 p-0.5 text-white shadow-md transition-colors hover:bg-red-600"
                      onClick={clearReferenceImage}
                    >
                      <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-medium text-gray-700">{referenceImageName}</div>
                    <div className="text-[10px] text-green-600">✓ 将发送给生图模型</div>
                  </div>
                </div>
              ) : (
                <div
                  className="flex cursor-pointer items-center gap-3 py-1"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100">
                    <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
                    </svg>
                  </div>
                  <div>
                    <div className="text-xs text-gray-600">点击上传角色参考图</div>
                    <div className="text-[10px] text-gray-400">图片将发送给生图模型作为参考</div>
                  </div>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleImageUpload}
              />
            </div>
          </div>

          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs">📝</span>
              生图提示词
            </h3>
            {generatedPrompt && (
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-600 transition-colors hover:bg-gray-50 disabled:opacity-50 disabled:hover:bg-transparent"
                  onClick={translatePrompt}
                  disabled={!generatedPrompt || translating || !hasEnglish(generatedPrompt)}
                  title="翻译为中文"
                >
                  {translating ? "翻译中..." : "翻译"}
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-600 transition-colors hover:bg-gray-50"
                  onClick={() => copyToClipboard(generatedPrompt)}
                >
                  复制
                </button>
              </div>
            )}
          </div>

          {/* 提示词结果展示/编辑 */}
          <div className="mb-4 flex flex-1 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white">
            {promptLoading ? (
              <div className="flex h-full items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
                  <div className="text-sm text-gray-500">正在处理信息...</div>
                </div>
              </div>
            ) : promptError ? (
              <div className="m-3 rounded-lg bg-red-50 p-3 text-sm text-red-600">
                {promptError}
              </div>
            ) : (
              <div className="flex flex-1 flex-col overflow-hidden p-3">
                {/* 固定提示词前缀 */}
                <div className="mb-3 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
                  <div className="mb-1 flex items-center gap-1 text-[10px] font-medium text-amber-600">
                    <span>📌</span>
                    固定前缀（自动添加）
                  </div>
                  <div className="font-mono text-xs leading-relaxed text-amber-800">
                    {FIXED_PROMPT_PREFIX}
                  </div>
                </div>
                {/* 可编辑的提示词输入框 */}
                <div className="flex flex-1 flex-col min-h-0">
                  <div className="mb-1 flex items-center justify-between">
                    <div className="text-[10px] font-medium text-gray-400">
                      {generatedPrompt ? "LLM 生成内容（可编辑）" : "提示词（可手动输入）"}
                    </div>
                    {generatedPrompt && (
                      <button
                        type="button"
                        className="text-[10px] text-indigo-500 hover:text-indigo-600"
                        onClick={() => setGeneratedPrompt("")}
                      >
                        清空
                      </button>
                    )}
                  </div>
                  <textarea
                    className="flex-1 min-h-[120px] w-full resize-none rounded-lg border border-gray-200 bg-gray-50/50 px-3 py-2 font-mono text-sm leading-relaxed text-gray-800 outline-none placeholder:text-gray-400 focus:border-indigo-500 focus:bg-white focus:ring-1 focus:ring-indigo-500"
                    placeholder="等待 LLM 生成提示词，或手动输入..."
                    value={generatedPrompt}
                    onChange={(e) => setGeneratedPrompt(e.target.value)}
                  />
                </div>
                {translation && (
                  <div className="mt-3 border-t border-gray-200 pt-3">
                    <div className="mb-1 text-xs text-gray-400">中文翻译</div>
                    <div className="whitespace-pre-wrap text-sm text-gray-600">
                      {translation}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 生图提供商选择 */}
          <div className="mb-3">
            <label className="mb-2 flex items-center gap-1 text-sm font-medium text-gray-700">
              <span>🔌</span>
              生图服务
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                className={`flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
                  imageProvider === "openrouter"
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                    : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                }`}
                onClick={() => setImageProvider("openrouter")}
              >
                OpenRouter
              </button>
              <button
                type="button"
                className={`flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
                  imageProvider === "fal"
                    ? "border-purple-500 bg-purple-50 text-purple-700"
                    : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                }`}
                onClick={() => setImageProvider("fal")}
              >
                fal.ai
              </button>
            </div>
          </div>

          {/* fal.ai API Key 输入 */}
          {imageProvider === "fal" && (
            <div className="mb-3">
              <label className="mb-2 flex items-center gap-1 text-sm font-medium text-gray-700">
                <span>🔑</span>
                fal.ai API Key
              </label>
              <input
                type="password"
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none placeholder:text-gray-400 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20"
                placeholder="输入 fal.ai API Key..."
                value={falApiKey}
                onChange={(e) => setFalApiKey(e.target.value)}
              />
              <div className="mt-1 text-[10px] text-gray-400">
                在{" "}
                <a
                  href="https://fal.ai/dashboard/keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-purple-500 hover:underline"
                >
                  fal.ai/dashboard/keys
                </a>{" "}
                获取
              </div>
            </div>
          )}

          {/* 生图模型选择 */}
          <div className="mb-3">
            <label className="mb-2 flex items-center gap-1 text-sm font-medium text-gray-700">
              <span>🎨</span>
              生图模型
            </label>
            {imageProvider === "openrouter" ? (
              <select
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                value={imageGenModelId}
                onChange={(e) => handleImageModelChange(e.target.value)}
              >
                {IMAGE_GEN_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            ) : (
              <select
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20"
                value={falModelId}
                onChange={(e) => setFalModelId(e.target.value)}
              >
                {FAL_IMAGE_MODELS.map((m) => (
                  <option key={m.id} value={m.id} title={m.description}>
                    {m.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* 图片尺寸选择 */}
          <div className="mb-4">
            <label className="mb-2 flex items-center gap-1 text-sm font-medium text-gray-700">
              <span>📐</span>
              图片尺寸
            </label>
            {imageProvider === "openrouter" ? (
              <select
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                value={imageSize}
                onChange={(e) => setImageSize(e.target.value as ImageSize)}
              >
                {getSupportedSizesForModel(imageGenModelId).map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            ) : (
              <select
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20"
                value={falImageSize}
                onChange={(e) => setFalImageSize(e.target.value as FalImageSize)}
              >
                {FAL_IMAGE_SIZES.map((size) => (
                  <option key={size.value} value={size.value}>
                    {size.label}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* 生成图片按钮 */}
          <button
            type="button"
            className="w-full rounded-xl border-2 border-indigo-600 bg-white px-6 py-3 text-sm font-semibold text-indigo-600 transition-all hover:bg-indigo-50 disabled:opacity-50"
            onClick={generateImage}
            disabled={!generatedPrompt || imageLoading}
          >
            {imageLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                图片生成中...
              </span>
            ) : (
              "🖼️ 生成图片"
            )}
          </button>
        </section>

        {/* 右侧：图片结果 */}
        <section className="col-span-4 flex h-full flex-col overflow-y-auto bg-gradient-to-b from-slate-50 to-slate-100 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-purple-100 text-xs">🖼️</span>
              生成结果
            </h3>
            {generatedImageUrl && (
              <button
                type="button"
                className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600 transition-colors hover:bg-gray-50"
                onClick={() => downloadImage(generatedImageUrl, `message-to-image-${Date.now()}.png`)}
              >
                下载
              </button>
            )}
          </div>

          {/* 图片展示区 */}
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
            {imageLoading ? (
              <div className="flex flex-col items-center gap-4">
                <div className="relative">
                  <div className="h-14 w-14 animate-pulse rounded-full bg-gradient-to-r from-indigo-400 to-purple-400" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <svg className="h-7 w-7 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </div>
                </div>
                <div className="text-sm text-gray-500">图片生成中...</div>
                <div className="text-xs text-gray-400">预计 10-30 秒</div>
              </div>
            ) : imageError ? (
              <div className="max-w-full w-full overflow-auto rounded-lg bg-red-50 p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-medium text-red-700">
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    生成失败
                  </div>
                  <button
                    type="button"
                    className="rounded bg-red-100 px-2 py-1 text-[10px] text-red-600 hover:bg-red-200"
                    onClick={() => copyToClipboard(imageError)}
                  >
                    复制错误
                  </button>
                </div>
                <div className="max-h-[300px] overflow-y-auto whitespace-pre-wrap break-words rounded border border-red-200 bg-white p-3 font-mono text-xs text-red-600">
                  {imageError}
                </div>
              </div>
            ) : generatedImageUrl ? (
              <div className="flex h-full w-full flex-col items-center justify-center gap-3">
                <img
                  src={generatedImageUrl}
                  alt="Generated"
                  className="max-h-[55vh] max-w-full cursor-pointer rounded-xl object-contain shadow-lg transition-transform hover:scale-[1.02]"
                  onClick={() => setPreviewImage(generatedImageUrl)}
                />
                {imageGenerationTime !== null && (
                  <div className="flex items-center gap-1.5 rounded-lg bg-green-50 px-3 py-1.5 text-xs text-green-700">
                    <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>
                      生成耗时：
                      {imageGenerationTime >= 1000
                        ? `${(imageGenerationTime / 1000).toFixed(1)} 秒`
                        : `${imageGenerationTime} 毫秒`}
                    </span>
                  </div>
                )}
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="rounded-lg bg-gray-900 px-3 py-1.5 text-xs text-white transition-colors hover:bg-gray-800"
                    onClick={() => setPreviewImage(generatedImageUrl)}
                  >
                    🔍 放大
                  </button>
                  <button
                    type="button"
                    className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-700 transition-colors hover:bg-gray-50"
                    onClick={() => downloadImage(generatedImageUrl, `message-to-image-${Date.now()}.png`)}
                  >
                    💾 下载
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center text-gray-400">
                <svg className="mb-3 h-16 w-16 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={0.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <div className="text-sm">等待生成图片...</div>
                <div className="mt-1 text-xs">生成提示词后点击生成</div>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* 图片预览弹窗 */}
      {previewImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
          onClick={() => setPreviewImage(null)}
        >
          <div className="relative max-h-[95vh] max-w-[95vw]">
            <img
              src={previewImage}
              alt="Preview"
              className="max-h-[95vh] max-w-[95vw] rounded-lg object-contain shadow-2xl"
            />
            <button
              type="button"
              className="absolute -right-3 -top-3 rounded-full bg-white p-2.5 shadow-lg transition-colors hover:bg-gray-100"
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
