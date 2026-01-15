"use client";

import { useRef, useState, useCallback, ChangeEvent } from "react";
import { useLocalStorageState } from "@/lib/useLocalStorageState";

const LS_NANO_BANANA_INSTRUCTION = "mychatplayground.nanoBanana.instruction";
const LS_NANO_BANANA_VARIABLES = "mychatplayground.nanoBanana.variables";

// Gemini 模型配置
const GEMINI_MODEL = {
  id: "gemini-2.0-flash-exp",
  name: "Gemini 2.0 Flash (图像生成)",
  description: "Google Gemini 原生图像生成，支持参考图",
};

// Python 后端 API 地址
const BACKEND_API_URL = "http://localhost:5001";

// 变量类型
type Variable = {
  id: string;
  name: string;
  value: string;
};

// 默认变量
const DEFAULT_VARIABLES: Variable[] = [
  { id: "1", name: "chat_history", value: "" },
  { id: "2", name: "user_info", value: "" },
];

// 默认指令
const DEFAULT_INSTRUCTION = `【聊天记录】
{chat_history}

【角色信息】
{user_info}

请根据以上信息，生成一张符合场景氛围的角色图片。`;


export default function NanoBananaPage() {
  // 指令管理：保存版本 vs 当前编辑
  const [savedInstruction, setSavedInstruction] = useLocalStorageState<string>(
    LS_NANO_BANANA_INSTRUCTION,
    DEFAULT_INSTRUCTION
  );
  const [instruction, setInstruction] = useState<string>(savedInstruction);
  const hasUnsavedChanges = instruction !== savedInstruction;

  // 变量管理
  const [variables, setVariables] = useLocalStorageState<Variable[]>(
    LS_NANO_BANANA_VARIABLES,
    DEFAULT_VARIABLES
  );
  const [editingVarId, setEditingVarId] = useState<string | null>(null);
  const [tempVarName, setTempVarName] = useState("");

  // 参考图 1：AI 角色的形象
  const [referenceImage1, setReferenceImage1] = useState<string | null>(null);
  const [referenceImage1Name, setReferenceImage1Name] = useState<string>("");
  const fileInputRef1 = useRef<HTMLInputElement>(null);

  // 参考图 2：用户本人的形象
  const [referenceImage2, setReferenceImage2] = useState<string | null>(null);
  const [referenceImage2Name, setReferenceImage2Name] = useState<string>("");
  const fileInputRef2 = useRef<HTMLInputElement>(null);

  // 图片生成状态
  const [imageLoading, setImageLoading] = useState(false);
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [imageGenerationTime, setImageGenerationTime] = useState<number | null>(null);
  
  // 调试信息：发送给模型的完整请求
  const [debugRequest, setDebugRequest] = useState<Array<{type: string; content: string}> | null>(null);

  // 图片预览弹窗
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  // 保存指令
  const saveInstruction = () => {
    setSavedInstruction(instruction);
  };

  // 处理图片上传（通用函数）
  const handleImageUpload = (
    e: ChangeEvent<HTMLInputElement>,
    setImage: (img: string | null) => void,
    setImageName: (name: string) => void
  ) => {
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
        setImage(result);
        setImageName(file.name);
      }
    };
    reader.readAsDataURL(file);
  };

  // 清除参考图 1
  const clearReferenceImage1 = () => {
    setReferenceImage1(null);
    setReferenceImage1Name("");
    if (fileInputRef1.current) {
      fileInputRef1.current.value = "";
    }
  };

  // 清除参考图 2
  const clearReferenceImage2 = () => {
    setReferenceImage2(null);
    setReferenceImage2Name("");
    if (fileInputRef2.current) {
      fileInputRef2.current.value = "";
    }
  };

  // 更新变量值
  const updateVariableValue = (id: string, value: string) => {
    setVariables(variables.map((v) => (v.id === id ? { ...v, value } : v)));
  };

  // 更新变量名
  const updateVariableName = (id: string, name: string) => {
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
    if (variables.length <= 1) return;
    setVariables(variables.filter((v) => v.id !== id));
  };

  // 将变量替换到指令中
  const replaceVariablesInInstruction = (inst: string): string => {
    let result = inst;
    for (const variable of variables) {
      const pattern = new RegExp(`\\{${variable.name}\\}`, "g");
      result = result.replace(pattern, variable.value || `[${variable.name} 未填写]`);
    }
    return result;
  };

  // 插入变量到指令
  const insertVariableToInstruction = (varName: string) => {
    setInstruction(instruction + `{${varName}}`);
  };

  // 检查是否有变量内容
  const hasVariableContent = variables.some((v) => v.value.trim());

  // 生成图片（调用 Gemini Python 后端）
  const generateImage = useCallback(async () => {
    if (!hasVariableContent && !instruction.trim()) {
      setImageError("请填写变量内容或指令");
      return;
    }

    const startTime = Date.now();
    setImageLoading(true);
    setGeneratedImageUrl(null);
    setImageError(null);
    setImageGenerationTime(null);
    setDebugRequest(null);

    try {
      // 构建完整的 prompt：将变量替换到指令中
      const prompt = replaceVariablesInInstruction(instruction);

      // 收集参考图 (base64)
      const referenceImages: string[] = [];
      if (referenceImage1) {
        referenceImages.push(referenceImage1);
      }
      if (referenceImage2) {
        referenceImages.push(referenceImage2);
      }

      const body = {
        prompt: prompt,
        reference_images: referenceImages,
      };

      console.log("Gemini API 请求:", { ...body, reference_images: referenceImages.map(() => "[base64 image]") });

      const response = await fetch(`${BACKEND_API_URL}/api/generate-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `API error: ${response.status}`);
      }

      if (!data.image) {
        throw new Error(data.error || "No image in response");
      }

      const endTime = Date.now();
      setImageGenerationTime(endTime - startTime);
      setGeneratedImageUrl(data.image);
      // 保存调试信息
      if (data.debug_request) {
        setDebugRequest(data.debug_request);
      }
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      
      // 检测内容政策违规错误
      if (errorMsg.includes("SAFETY") || errorMsg.includes("blocked")) {
        setImageError(
          "⚠️ 内容政策违规\n\n" +
          "Gemini 检测到 prompt 中包含敏感内容，已拦截此请求。\n\n" +
          "解决方案：\n" +
          "• 修改对话内容，移除敏感描述\n" +
          "• 使用更温和的场景描述\n\n" +
          "原始错误：\n" + errorMsg
        );
      } else {
        setImageError(errorMsg);
      }
    } finally {
      setImageLoading(false);
    }
  }, [instruction, referenceImage1, referenceImage2, hasVariableContent, replaceVariablesInInstruction]);

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

  return (
    <div className="h-full w-full bg-white text-gray-900">
      <div className="grid h-full grid-cols-12 gap-0">
        {/* 左侧：变量管理 + 指令编辑 */}
        <section className="col-span-5 flex h-full flex-col overflow-y-auto border-r border-gray-200 bg-gradient-to-b from-amber-50/50 to-white p-4">
          <div className="mb-4">
            <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <span className="text-2xl">🍌</span>
              Nano Banana 消息生图
            </h2>
            <p className="mt-1 text-xs text-gray-500">
              一步到位：Nano Banana 直接理解消息并生成图片
            </p>
          </div>

          {/* 模型信息 - Gemini */}
          <div className="mb-4 rounded-xl border border-blue-200 bg-blue-50 p-3">
            <div className="flex items-center gap-2">
              <span className="text-lg">✨</span>
              <div>
                <div className="text-sm font-medium text-blue-900">
                  {GEMINI_MODEL.name}
                </div>
                <div className="text-xs text-blue-700">
                  {GEMINI_MODEL.description}
                </div>
                <div className="mt-1 font-mono text-[10px] text-blue-600">
                  {GEMINI_MODEL.id}
                </div>
              </div>
            </div>
            {(referenceImage1 || referenceImage2) && (
              <div className="mt-2 rounded-lg bg-blue-100 px-2 py-1 text-[10px] text-blue-700">
                ✓ 已上传参考图，Gemini 将参考这些图片生成
              </div>
            )}
          </div>

          {/* 变量管理区域 */}
          <div className="mb-4">
            <div className="mb-2 flex items-center justify-between">
              <label className="flex items-center gap-1 text-sm font-medium text-gray-700">
                <span>📦</span>
                变量配置
              </label>
              <button
                type="button"
                className="flex items-center gap-1 rounded-lg bg-amber-50 px-2 py-1 text-xs text-amber-700 transition-colors hover:bg-amber-100"
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
                          className="w-32 rounded border border-amber-300 bg-amber-50 px-2 py-0.5 font-mono text-xs text-amber-700 outline-none"
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
                          className="cursor-pointer rounded bg-amber-50 px-2 py-0.5 font-mono text-xs text-amber-700 hover:bg-amber-100"
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
                        title="插入到指令"
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
                    className="w-full resize-none rounded-lg border border-gray-200 bg-gray-50/50 px-3 py-2 text-xs text-gray-900 outline-none placeholder:text-gray-400 focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
                    rows={3}
                    placeholder={`输入 ${variable.name} 的内容...`}
                    value={variable.value}
                    onChange={(e) => updateVariableValue(variable.id, e.target.value)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* 指令编辑窗口 */}
          <div className="mb-4 flex flex-1 flex-col">
            <div className="mb-2 flex items-center justify-between">
              <label className="flex items-center gap-1 text-sm font-medium text-gray-700">
                <span>📜</span>
                生图指令
                {hasUnsavedChanges && (
                  <span className="ml-1 text-[10px] text-amber-500">● 未保存</span>
                )}
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className={`rounded-lg px-2 py-1 text-xs font-medium transition-colors ${
                    hasUnsavedChanges
                      ? "bg-amber-500 text-white hover:bg-amber-600"
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
                  className="text-xs text-amber-600 hover:text-amber-700"
                  onClick={() => setInstruction(DEFAULT_INSTRUCTION)}
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
                  className="rounded bg-amber-50 px-1.5 py-0.5 font-mono text-[10px] text-amber-700 hover:bg-amber-100"
                  onClick={() => insertVariableToInstruction(v.name)}
                  title={`点击插入 {${v.name}}`}
                >
                  {`{${v.name}}`}
                </button>
              ))}
            </div>
            <textarea
              className={`min-h-[150px] flex-1 w-full resize-none rounded-xl border bg-white px-3 py-2 font-mono text-xs text-gray-900 shadow-sm outline-none placeholder:text-gray-400 focus:ring-2 focus:ring-amber-500/20 ${
                hasUnsavedChanges
                  ? "border-amber-300 focus:border-amber-400"
                  : "border-gray-200 focus:border-amber-500"
              }`}
              placeholder="输入生图指令，使用 {变量名} 引用变量内容..."
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
            />
          </div>

          {/* 参考图上传区域 */}
          <div className="mb-4">
            <label className="mb-2 flex items-center gap-1 text-sm font-medium text-gray-700">
              <span>🖼️</span>
              参考图上传（可选）
            </label>
            
            <div className="space-y-3">
              {/* 参考图 1：AI 角色的形象 */}
              <div className="rounded-xl border-2 border-dashed border-purple-200 bg-purple-50/30 p-3 transition-colors hover:border-purple-400">
                <div className="mb-2 flex items-center gap-1.5">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-purple-100 text-xs font-bold text-purple-600">1</span>
                  <span className="text-xs font-medium text-purple-700">AI 角色的形象</span>
                  <span className="text-[10px] text-purple-500">（发型、五官、身材等外观特征）</span>
                </div>
                {referenceImage1 ? (
                  <div className="flex items-center gap-3">
                    <div className="relative flex-shrink-0">
                      <img
                        src={referenceImage1}
                        alt="AI角色参考图"
                        className="h-16 w-16 cursor-pointer rounded-lg object-cover shadow-sm transition-transform hover:scale-105"
                        onClick={() => setPreviewImage(referenceImage1)}
                      />
                      <button
                        type="button"
                        className="absolute -right-1.5 -top-1.5 rounded-full bg-red-500 p-0.5 text-white shadow-md transition-colors hover:bg-red-600"
                        onClick={clearReferenceImage1}
                      >
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs font-medium text-gray-700">{referenceImage1Name}</div>
                      <div className="text-[10px] text-green-600">✓ AI 角色参考图已上传</div>
                    </div>
                  </div>
                ) : (
                  <div
                    className="flex cursor-pointer items-center gap-3 py-1"
                    onClick={() => fileInputRef1.current?.click()}
                  >
                    <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-purple-100">
                      <svg className="h-5 w-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
                      </svg>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">点击上传 AI 角色参考图</div>
                      <div className="text-[10px] text-gray-400">用于保持角色外观一致性</div>
                    </div>
                  </div>
                )}
                <input
                  ref={fileInputRef1}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => handleImageUpload(e, setReferenceImage1, setReferenceImage1Name)}
                />
              </div>

              {/* 参考图 2：用户本人的形象 */}
              <div className="rounded-xl border-2 border-dashed border-blue-200 bg-blue-50/30 p-3 transition-colors hover:border-blue-400">
                <div className="mb-2 flex items-center gap-1.5">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-600">2</span>
                  <span className="text-xs font-medium text-blue-700">用户本人的形象</span>
                  <span className="text-[10px] text-blue-500">（如需用户出现在画面中）</span>
                </div>
                {referenceImage2 ? (
                  <div className="flex items-center gap-3">
                    <div className="relative flex-shrink-0">
                      <img
                        src={referenceImage2}
                        alt="用户参考图"
                        className="h-16 w-16 cursor-pointer rounded-lg object-cover shadow-sm transition-transform hover:scale-105"
                        onClick={() => setPreviewImage(referenceImage2)}
                      />
                      <button
                        type="button"
                        className="absolute -right-1.5 -top-1.5 rounded-full bg-red-500 p-0.5 text-white shadow-md transition-colors hover:bg-red-600"
                        onClick={clearReferenceImage2}
                      >
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs font-medium text-gray-700">{referenceImage2Name}</div>
                      <div className="text-[10px] text-green-600">✓ 用户参考图已上传</div>
                    </div>
                  </div>
                ) : (
                  <div
                    className="flex cursor-pointer items-center gap-3 py-1"
                    onClick={() => fileInputRef2.current?.click()}
                  >
                    <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-blue-100">
                      <svg className="h-5 w-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
                      </svg>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">点击上传用户参考图</div>
                      <div className="text-[10px] text-gray-400">用于用户出现在画面中的场景</div>
                    </div>
                  </div>
                )}
                <input
                  ref={fileInputRef2}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => handleImageUpload(e, setReferenceImage2, setReferenceImage2Name)}
                />
              </div>
            </div>
          </div>

          {/* 生成图片按钮 */}
          <button
            type="button"
            className="w-full rounded-xl bg-gradient-to-r from-blue-500 to-indigo-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/30 transition-all hover:from-blue-600 hover:to-indigo-600 hover:shadow-blue-500/40 disabled:opacity-50 disabled:shadow-none"
            onClick={generateImage}
            disabled={imageLoading}
          >
            {imageLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                生成中...
              </span>
            ) : (
              "✨ 一键生成图片"
            )}
          </button>
        </section>

        {/* 右侧：图片结果 */}
        <section className="col-span-7 flex h-full flex-col overflow-y-auto bg-gradient-to-b from-orange-50/30 to-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 text-xs">🖼️</span>
              生成结果
            </h3>
            {generatedImageUrl && (
              <button
                type="button"
                className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600 transition-colors hover:bg-gray-50"
                onClick={() => downloadImage(generatedImageUrl, `gemini-${Date.now()}.png`)}
              >
                下载
              </button>
            )}
          </div>

          {/* 预览完整的 API 请求信息 */}
          {(hasVariableContent || instruction.trim()) && (
            <div className="mb-4 rounded-xl border border-gray-200 bg-white p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-xs font-medium text-gray-500">📋 API 请求详情</div>
                <button
                  type="button"
                  className="text-[10px] text-gray-400 hover:text-gray-600"
                  onClick={() => {
                    const refImages: string[] = [];
                    if (referenceImage1) refImages.push("[参考图1:AI角色]");
                    if (referenceImage2) refImages.push("[参考图2:用户]");
                    copyToClipboard(JSON.stringify({
                      endpoint: `${BACKEND_API_URL}/api/generate-image`,
                      model: GEMINI_MODEL.id,
                      image_size: "1024x1024 (固定)",
                      reference_images: refImages,
                      prompt: replaceVariablesInInstruction(instruction),
                    }, null, 2));
                  }}
                >
                  复制 JSON
                </button>
              </div>
              
              {/* API 配置信息 */}
              <div className="mb-3 space-y-1.5 rounded-lg bg-blue-50 p-2">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-blue-700">🔗 端点：</span>
                  <code className="rounded bg-blue-100 px-1.5 py-0.5 font-mono text-[10px] text-blue-800">
                    {BACKEND_API_URL}/api/generate-image
                  </code>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-blue-700">✨ 模型：</span>
                  <code className="rounded bg-blue-100 px-1.5 py-0.5 font-mono text-[10px] text-blue-800">
                    {GEMINI_MODEL.id}
                  </code>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-blue-700">📐 尺寸：</span>
                  <code className="rounded bg-blue-100 px-1.5 py-0.5 font-mono text-[10px] text-blue-800">
                    1024×1024
                  </code>
                  <span className="text-[10px] text-blue-600">
                    (固定尺寸)
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-blue-700">🖼️ 参考图 1 (AI角色)：</span>
                  <span className={`rounded px-1.5 py-0.5 text-[10px] ${
                    referenceImage1 
                      ? "bg-green-100 text-green-700" 
                      : "bg-gray-100 text-gray-500"
                  }`}>
                    {referenceImage1 ? "✓ 已上传" : "未上传"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-blue-700">🖼️ 参考图 2 (用户)：</span>
                  <span className={`rounded px-1.5 py-0.5 text-[10px] ${
                    referenceImage2 
                      ? "bg-green-100 text-green-700" 
                      : "bg-gray-100 text-gray-500"
                  }`}>
                    {referenceImage2 ? "✓ 已上传" : "未上传"}
                  </span>
                </div>
                {(referenceImage1 || referenceImage2) && (
                  <div className="mt-1 rounded bg-blue-100 px-2 py-1 text-[10px] text-blue-700">
                    📎 reference_images: [{referenceImage1 ? "参考图1" : ""}{referenceImage1 && referenceImage2 ? ", " : ""}{referenceImage2 ? "参考图2" : ""}]
                  </div>
                )}
              </div>

              {/* Prompt 内容 */}
              <div className="text-xs font-medium text-gray-500 mb-1">📝 Prompt 内容：</div>
              <div className="max-h-[300px] overflow-y-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-2 text-xs text-gray-700">
                {replaceVariablesInInstruction(instruction)}
              </div>
            </div>
          )}

          {/* 🔍 发送给模型的完整请求（调试信息） */}
          {debugRequest && debugRequest.length > 0 && (
            <div className="mb-4 rounded-xl border-2 border-purple-300 bg-purple-50 p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-xs font-medium text-purple-700">🔍 发送给模型的完整请求（调试视图）</div>
                <span className="rounded bg-purple-200 px-2 py-0.5 text-[10px] text-purple-700">
                  共 {debugRequest.length} 个部分
                </span>
              </div>
              <div className="space-y-2">
                {debugRequest.map((part, index) => (
                  <div key={index} className={`rounded-lg p-2 ${
                    part.type === "image" 
                      ? "bg-green-100 border border-green-300" 
                      : "bg-white border border-purple-200"
                  }`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        part.type === "image"
                          ? "bg-green-200 text-green-800"
                          : "bg-purple-200 text-purple-800"
                      }`}>
                        {part.type === "image" ? "🖼️ 图片" : "📝 文本"} #{index + 1}
                      </span>
                    </div>
                    <div className="whitespace-pre-wrap text-xs text-gray-700 max-h-[200px] overflow-y-auto">
                      {part.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 图片展示区 */}
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
            {imageLoading ? (
              <div className="flex flex-col items-center gap-4">
                <div className="relative">
                  <div className="h-14 w-14 animate-pulse rounded-full bg-gradient-to-r from-amber-400 to-orange-400" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <svg className="h-7 w-7 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </div>
                </div>
                <div className="text-sm text-gray-500">✨ Gemini 正在生成图片...</div>
                <div className="text-xs text-gray-400">预计 10-60 秒</div>
              </div>
            ) : imageError ? (
              imageError.includes("内容政策违规") ? (
                // 内容政策违规 - 特殊显眼样式
                <div className="max-w-full w-full overflow-auto">
                  <div className="rounded-2xl border-2 border-orange-400 bg-gradient-to-br from-orange-50 to-amber-50 p-6 shadow-lg">
                    {/* 大图标 */}
                    <div className="mb-4 flex justify-center">
                      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-orange-100">
                        <span className="text-5xl">🚫</span>
                      </div>
                    </div>
                    
                    {/* 标题 */}
                    <h3 className="mb-3 text-center text-xl font-bold text-orange-700">
                      内容安全限制
                    </h3>
                    
                    {/* 说明 */}
                    <div className="mb-4 rounded-xl bg-white/80 p-4 text-center">
                      <p className="text-sm text-gray-700">
                        fal.ai 检测到 Prompt 中包含<strong className="text-orange-600">敏感内容</strong>
                        <br />
                        （如成人/暴力/违规内容），已拦截此请求
                      </p>
                    </div>
                    
                    {/* 解决方案 */}
                    <div className="mb-4 rounded-xl bg-white p-4">
                      <div className="mb-2 text-sm font-semibold text-gray-800">💡 解决方案：</div>
                      <ul className="space-y-2 text-sm text-gray-600">
                        <li className="flex items-start gap-2">
                          <span className="mt-0.5 text-green-500">✓</span>
                          <span>修改<strong>变量内容</strong>中的对话，移除敏感描述</span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="mt-0.5 text-green-500">✓</span>
                          <span>使用更温和、安全的场景描述</span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="mt-0.5 text-green-500">✓</span>
                          <span>避免包含成人、暴力、血腥等内容</span>
                        </li>
                      </ul>
                    </div>
                    
                    {/* 折叠的原始错误 */}
                    <details className="rounded-lg bg-gray-100 p-2">
                      <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
                        查看原始错误信息
                      </summary>
                      <div className="mt-2 max-h-[150px] overflow-y-auto whitespace-pre-wrap break-words rounded bg-white p-2 font-mono text-[10px] text-gray-500">
                        {imageError}
                      </div>
                    </details>
                  </div>
                </div>
              ) : (
                // 普通错误样式
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
              )
            ) : generatedImageUrl ? (
              <div className="flex h-full w-full flex-col items-center justify-center gap-3">
                <img
                  src={generatedImageUrl}
                  alt="Generated"
                  className="max-h-[60vh] max-w-full cursor-pointer rounded-xl object-contain shadow-lg transition-transform hover:scale-[1.02]"
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
                    onClick={() => downloadImage(generatedImageUrl, `gemini-${Date.now()}.png`)}
                  >
                    💾 下载
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center text-gray-400">
                <div className="mb-3 text-6xl opacity-30">✨</div>
                <div className="text-sm">等待生成图片...</div>
                <div className="mt-1 text-xs">填写内容后点击「一键生成图片」</div>
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
