/**
 * CREATED_BY_AGENT
 */
import { describe, expect, it } from "vitest";
import type {
  GeneratedImage,
  UserAnalyticsReportGeneratedImageItem,
} from "../types";
import {
  buildGeneratedImageDetailFromDailyReportItem,
  buildGeneratedImageDetailFromGeneratedImage,
  extractGeneratedImageModel,
} from "../utils/generatedImageDetail";

describe("generatedImageDetail", () => {
  it("extracts model from report metadata", () => {
    const model = extractGeneratedImageModel({
      generated_image: {
        model: "gemini-2.5-flash-image",
      },
    });
    expect(model).toBe("gemini-2.5-flash-image");
  });

  it("returns null model for invalid metadata", () => {
    expect(extractGeneratedImageModel(null)).toBeNull();
    expect(
      extractGeneratedImageModel({ generated_image: "not-an-object" }),
    ).toBeNull();
  });

  it("builds detail data from daily report item", () => {
    const reportItem: UserAnalyticsReportGeneratedImageItem = {
      id: 1,
      session_id: "session-1",
      image_url: "https://cdn.example.com/image.webp",
      meta_data: {
        user_id: "user-1",
        langsmith_trace_id: "trace-123",
        langsmith_trace_url:
          "https://smith.langchain.com/o/x/projects/p/y/r/trace-123",
        user_reference_image_url: "https://cdn.example.com/selfie.webp",
        generated_image: {
          image_url: "gs://bucket/image.webp",
          prompt: "test prompt",
          original_request: "请基于这段对话生成一张图片",
          reference_image_url: "https://cdn.example.com/ref.webp",
          user_reference_image_url: "https://cdn.example.com/selfie.webp",
          reference_image_urls: [
            "https://cdn.example.com/ref.webp",
            "https://cdn.example.com/selfie.webp",
          ],
          width: 768,
          height: 1024,
          model: "openai/gpt-image-1",
          generation_mode: "fallback_matched_image",
          is_matched: true,
          generation_time_ms: 2450,
          model_fallback_due_to_429: true,
        },
      },
      created_at: "2026-02-27T08:10:49+00:00",
    };

    const detail = buildGeneratedImageDetailFromDailyReportItem(reportItem);
    expect(detail.imageUrl).toBe("https://cdn.example.com/image.webp");
    expect(detail.gcsUrl).toBe("gs://bucket/image.webp");
    expect(detail.generationPrompt).toBe("test prompt");
    expect(detail.originalRequest).toBe("请基于这段对话生成一张图片");
    expect(detail.referenceImageUrl).toBe("https://cdn.example.com/ref.webp");
    expect(detail.userReferenceImageUrl).toBe(
      "https://cdn.example.com/selfie.webp",
    );
    expect(detail.referenceImages).toEqual([
      { label: "角色参考图", url: "https://cdn.example.com/ref.webp" },
      { label: "用户参考图", url: "https://cdn.example.com/selfie.webp" },
    ]);
    expect(detail.width).toBe(768);
    expect(detail.height).toBe(1024);
    expect(detail.userId).toBe("user-1");
    expect(detail.sessionId).toBe("session-1");
    expect(detail.model).toBe("openai/gpt-image-1");
    expect(detail.generationMode).toBe("fallback_matched_image");
    expect(detail.isMatchedFallback).toBe(true);
    expect(detail.generationTimeMs).toBe(2450);
    expect(detail.modelFallbackDueTo429).toBe(true);
    expect(detail.langsmithTraceId).toBe("trace-123");
    expect(detail.langsmithTraceUrl).toBe(
      "https://smith.langchain.com/o/x/projects/p/y/r/trace-123",
    );
  });

  it("falls back to synthesized metadata for generated image list item", () => {
    const image: GeneratedImage = {
      url: "https://cdn.example.com/generated.webp",
      gcs_url: "gs://bucket/generated.webp",
      generation_prompt: "fallback prompt",
      reference_image_url: null,
      user_reference_image_url: "https://cdn.example.com/selfie2.webp",
      width: 512,
      height: 512,
      created_at: null,
      user_id: "user-2",
      user_nickname: null,
      user_email: null,
      user_photo: null,
    };

    const detail = buildGeneratedImageDetailFromGeneratedImage(image);
    expect(detail.generationPrompt).toBe("fallback prompt");
    expect(detail.metaData.generated_image).toMatchObject({
      image_url: "gs://bucket/generated.webp",
      prompt: "fallback prompt",
      width: 512,
      height: 512,
    });
    expect(detail.referenceImages).toEqual([
      { label: "用户参考图", url: "https://cdn.example.com/selfie2.webp" },
    ]);
  });
});
