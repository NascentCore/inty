import { describe, it, expect, vi } from "vitest";
import { EMOTIONS, generateReplyWithEmotion } from "../services/gemini";

// Helper to mock fetch
const mockFetch = (payload: any, ok = true) => {
  // @ts-ignore
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Server Error",
    json: async () => payload,
    text: async () => JSON.stringify(payload),
  });
};

describe("gemini service", () => {
  it("returns parsed reply and valid emotion when JSON is correct", async () => {
    const output = { reply: "你好！", emotion: "Happy" };
    mockFetch({
      candidates: [{ content: { parts: [{ text: JSON.stringify(output) }] } }],
    });

    const res = await generateReplyWithEmotion("KEY", [], "hi");
    expect(res.reply).toBe("你好！");
    expect(EMOTIONS.includes(res.emotion)).toBe(true);
  });

  it("normalizes unknown emotion to Neutral", async () => {
    const output = { reply: "OK", emotion: "UnknownLabel" };
    mockFetch({
      candidates: [{ content: { parts: [{ text: JSON.stringify(output) }] } }],
    });

    const res = await generateReplyWithEmotion("KEY", [], "hi");
    expect(res.reply).toBe("OK");
    expect(res.emotion).toBe("Neutral");
  });

  it("extracts JSON from fenced or verbose output", async () => {
    const noisy =
      'Here is your result:\n```json\n{"reply":"Yo","emotion":"Excited"}\n```';
    mockFetch({ candidates: [{ content: { parts: [{ text: noisy }] } }] });

    const res = await generateReplyWithEmotion("KEY", [], "hi");
    expect(res.reply).toBe("Yo");
    expect(res.emotion).toBe("Excited");
  });

  it("falls back to Neutral if non-JSON", async () => {
    mockFetch({
      candidates: [{ content: { parts: [{ text: "plain text" }] } }],
    });

    const res = await generateReplyWithEmotion("KEY", [], "hi");
    expect(res.emotion).toBe("Neutral");
    expect(typeof res.reply).toBe("string");
  });

  it("throws when api key missing", async () => {
    await expect(generateReplyWithEmotion("", [], "hi")).rejects.toThrow();
  });

  it("throws when http error", async () => {
    // @ts-ignore
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "ERR",
      text: async () => "boom",
    });
    await expect(generateReplyWithEmotion("KEY", [], "hi")).rejects.toThrow();
  });
});
