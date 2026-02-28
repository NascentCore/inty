/**
 * 生成图片详情数据转换工具
 * CREATED_BY_AGENT
 */
import type {
  GeneratedImage,
  UserAnalyticsReportGeneratedImageItem,
} from "../types";

type UnknownRecord = Record<string, unknown>;

export interface GeneratedImageDetail {
  imageUrl: string;
  gcsUrl: string | null;
  generationPrompt: string | null;
  referenceImageUrl: string | null;
  width: number | null;
  height: number | null;
  createdAt: string | null;
  userId: string | null;
  sessionId: string | null;
  model: string | null;
  generationTimeMs: number | null;
  modelFallbackDueTo429: boolean | null;
  metaData: UnknownRecord;
}

interface ParsedGeneratedImageMeta {
  imageUrl: string | null;
  generationPrompt: string | null;
  referenceImageUrl: string | null;
  width: number | null;
  height: number | null;
  userId: string | null;
  sessionId: string | null;
  model: string | null;
  generationTimeMs: number | null;
  modelFallbackDueTo429: boolean | null;
}

function isRecord(value: unknown): value is UnknownRecord {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function readString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return null;
  }
  return trimmedValue;
}

function readNumber(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }
  return value;
}

function readBoolean(value: unknown): boolean | null {
  if (typeof value !== "boolean") {
    return null;
  }
  return value;
}

function readGeneratedImageMetaNode(
  metaData: UnknownRecord,
): UnknownRecord | null {
  const generatedImage = metaData.generated_image;
  if (!isRecord(generatedImage)) {
    return null;
  }
  return generatedImage;
}

function parseGeneratedImageMeta(metaData: UnknownRecord): ParsedGeneratedImageMeta {
  const generatedImage = readGeneratedImageMetaNode(metaData);
  return {
    imageUrl: readString(generatedImage?.image_url),
    generationPrompt:
      readString(generatedImage?.prompt) ??
      readString(generatedImage?.generation_prompt),
    referenceImageUrl: readString(generatedImage?.reference_image_url),
    width: readNumber(generatedImage?.width),
    height: readNumber(generatedImage?.height),
    userId: readString(metaData.user_id),
    sessionId: readString(metaData.session_id),
    model: readString(generatedImage?.model),
    generationTimeMs: readNumber(generatedImage?.generation_time_ms),
    modelFallbackDueTo429: readBoolean(
      generatedImage?.model_fallback_due_to_429,
    ),
  };
}

function buildFallbackMetaDataFromGeneratedImage(
  image: GeneratedImage,
): UnknownRecord {
  return {
    user_id: image.user_id,
    session_id: image.session_id,
    generated_image: {
      image_url: image.gcs_url || image.url,
      prompt: image.generation_prompt,
      reference_image_url: image.reference_image_url,
      width: image.width,
      height: image.height,
      model: image.model,
      generation_time_ms: image.generation_time_ms,
      model_fallback_due_to_429: image.model_fallback_due_to_429,
    },
  };
}

export function extractGeneratedImageModel(
  metaData: UnknownRecord | null | undefined,
): string | null {
  if (!isRecord(metaData)) {
    return null;
  }
  return parseGeneratedImageMeta(metaData).model;
}

export function buildGeneratedImageDetailFromDailyReportItem(
  item: UserAnalyticsReportGeneratedImageItem,
): GeneratedImageDetail {
  const normalizedMetaData = isRecord(item.meta_data) ? item.meta_data : {};
  const parsedMeta = parseGeneratedImageMeta(normalizedMetaData);
  return {
    imageUrl: item.image_url,
    gcsUrl: parsedMeta.imageUrl,
    generationPrompt: parsedMeta.generationPrompt,
    referenceImageUrl: parsedMeta.referenceImageUrl,
    width: parsedMeta.width,
    height: parsedMeta.height,
    createdAt: item.created_at,
    userId: parsedMeta.userId,
    sessionId: item.session_id,
    model: parsedMeta.model,
    generationTimeMs: parsedMeta.generationTimeMs,
    modelFallbackDueTo429: parsedMeta.modelFallbackDueTo429,
    metaData: normalizedMetaData,
  };
}

export function buildGeneratedImageDetailFromGeneratedImage(
  image: GeneratedImage,
): GeneratedImageDetail {
  const normalizedMetaData = isRecord(image.meta_data)
    ? image.meta_data
    : buildFallbackMetaDataFromGeneratedImage(image);
  const parsedMeta = parseGeneratedImageMeta(normalizedMetaData);
  return {
    imageUrl: image.url,
    gcsUrl: image.gcs_url || parsedMeta.imageUrl,
    generationPrompt: image.generation_prompt || parsedMeta.generationPrompt,
    referenceImageUrl:
      image.reference_image_url || parsedMeta.referenceImageUrl,
    width: image.width ?? parsedMeta.width,
    height: image.height ?? parsedMeta.height,
    createdAt: image.created_at,
    userId: image.user_id || parsedMeta.userId,
    sessionId: image.session_id || parsedMeta.sessionId,
    model: image.model ?? parsedMeta.model,
    generationTimeMs: image.generation_time_ms ?? parsedMeta.generationTimeMs,
    modelFallbackDueTo429:
      image.model_fallback_due_to_429 ?? parsedMeta.modelFallbackDueTo429,
    metaData: normalizedMetaData,
  };
}
