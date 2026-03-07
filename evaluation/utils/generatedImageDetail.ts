/**
 * 生成图片详情数据转换工具
 * CREATED_BY_AGENT
 */
import type {
  GeneratedImage,
  UserAnalyticsReportGeneratedImageItem,
} from "../types";

type UnknownRecord = Record<string, unknown>;

export interface GeneratedImageReferenceAsset {
  label: string;
  url: string;
}

export interface GeneratedImageDetail {
  imageUrl: string;
  gcsUrl: string | null;
  generationPrompt: string | null;
  referenceImageUrl: string | null;
  userReferenceImageUrl: string | null;
  referenceImages: GeneratedImageReferenceAsset[];
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
  userReferenceImageUrl: string | null;
  referenceImageUrls: string[];
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

function readStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => readString(item))
    .filter((item): item is string => item !== null);
}

function normalizeImageUrl(value: string): string {
  if (value.startsWith("gs://")) {
    return value.replace("gs://", "https://storage.googleapis.com/");
  }
  return value;
}

function isLikelyImageUrl(value: string): boolean {
  const normalizedUrl = normalizeImageUrl(value);
  return (
    normalizedUrl.startsWith("http://") || normalizedUrl.startsWith("https://")
  );
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

function parseGeneratedImageMeta(
  metaData: UnknownRecord,
): ParsedGeneratedImageMeta {
  const generatedImage = readGeneratedImageMetaNode(metaData);
  return {
    imageUrl: readString(generatedImage?.image_url),
    generationPrompt:
      readString(generatedImage?.prompt) ??
      readString(generatedImage?.generation_prompt),
    referenceImageUrl: readString(generatedImage?.reference_image_url),
    userReferenceImageUrl:
      readString(generatedImage?.user_reference_image_url) ??
      readString(metaData.user_reference_image_url) ??
      readString(metaData.user_photo_url),
    referenceImageUrls: readStringArray(generatedImage?.reference_image_urls),
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

function buildReferenceImageAssets({
  roleReferenceImageUrl,
  userReferenceImageUrl,
  extraReferenceImageUrls,
}: {
  roleReferenceImageUrl: string | null;
  userReferenceImageUrl: string | null;
  extraReferenceImageUrls: string[];
}): GeneratedImageReferenceAsset[] {
  const assets: GeneratedImageReferenceAsset[] = [];
  const visitedUrls = new Set<string>();
  const append = (url: string | null, label: string) => {
    if (!url) {
      return;
    }
    if (!isLikelyImageUrl(url)) {
      return;
    }
    const normalizedUrl = normalizeImageUrl(url);
    if (visitedUrls.has(normalizedUrl)) {
      return;
    }
    visitedUrls.add(normalizedUrl);
    assets.push({ label, url: normalizedUrl });
  };

  append(roleReferenceImageUrl, "角色参考图");
  append(userReferenceImageUrl, "用户参考图");
  extraReferenceImageUrls.forEach((url, index) => {
    append(url, `参考图 ${index + 1}`);
  });

  return assets;
}

function buildFallbackMetaDataFromGeneratedImage(
  image: GeneratedImage,
): UnknownRecord {
  const referenceImageUrls = [
    image.reference_image_url,
    image.user_reference_image_url,
  ]
    .map((value) => readString(value))
    .filter((value): value is string => value !== null);
  return {
    user_id: image.user_id,
    session_id: image.session_id,
    user_reference_image_url: image.user_reference_image_url,
    generated_image: {
      image_url: image.gcs_url || image.url,
      prompt: image.generation_prompt,
      reference_image_url: image.reference_image_url,
      user_reference_image_url: image.user_reference_image_url,
      reference_image_urls: referenceImageUrls,
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
  const roleReferenceImageUrl =
    parsedMeta.referenceImageUrl ??
    readString(normalizedMetaData.reference_image_url);
  const userReferenceImageUrl =
    parsedMeta.userReferenceImageUrl ??
    readString(normalizedMetaData.user_reference_image_url) ??
    readString(normalizedMetaData.user_photo_url);
  const referenceImages = buildReferenceImageAssets({
    roleReferenceImageUrl,
    userReferenceImageUrl,
    extraReferenceImageUrls: [
      ...parsedMeta.referenceImageUrls,
      ...readStringArray(normalizedMetaData.reference_image_urls),
    ],
  });
  return {
    imageUrl: item.image_url,
    gcsUrl: parsedMeta.imageUrl,
    generationPrompt: parsedMeta.generationPrompt,
    referenceImageUrl: roleReferenceImageUrl,
    userReferenceImageUrl,
    referenceImages,
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
  const roleReferenceImageUrl =
    image.reference_image_url ??
    parsedMeta.referenceImageUrl ??
    readString(normalizedMetaData.reference_image_url);
  const userReferenceImageUrl =
    image.user_reference_image_url ??
    parsedMeta.userReferenceImageUrl ??
    readString(normalizedMetaData.user_reference_image_url) ??
    readString(normalizedMetaData.user_photo_url);
  const combinedExtraReferenceImageUrls = [
    ...parsedMeta.referenceImageUrls,
    ...readStringArray(normalizedMetaData.reference_image_urls),
  ];
  const referenceImages = buildReferenceImageAssets({
    roleReferenceImageUrl,
    userReferenceImageUrl,
    extraReferenceImageUrls: combinedExtraReferenceImageUrls,
  });
  return {
    imageUrl: image.url,
    gcsUrl: image.gcs_url || parsedMeta.imageUrl,
    generationPrompt: image.generation_prompt || parsedMeta.generationPrompt,
    referenceImageUrl: roleReferenceImageUrl,
    userReferenceImageUrl,
    referenceImages,
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
