import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AgentInfoDisplay } from "../components/common/AgentInfoDisplay";
import type { Agent } from "../types";

const minimalAgent = (): Agent => ({
  id: "a",
  name: "Test",
  visibility: "PUBLIC",
  gender: "MALE",
});

describe("AgentInfoDisplay", () => {
  it("shows chat model id when llm_config.model is set", () => {
    const html = renderToStaticMarkup(
      <AgentInfoDisplay
        agent={{
          ...minimalAgent(),
          llm_config: {
            model: "google/gemini-2.5-flash",
            temperature: 0.7,
            max_tokens: 2048,
            top_p: 1,
            frequency_penalty: 0,
            presence_penalty: 0,
          },
        }}
        showImages={false}
        showPrompts={false}
        showLLMConfig={false}
      />,
    );
    expect(html.includes("对话模型:")).toBe(true);
    expect(html.includes("google/gemini-2.5-flash")).toBe(true);
  });

  it("shows platform default when llm_config is absent", () => {
    const html = renderToStaticMarkup(
      <AgentInfoDisplay
        agent={minimalAgent()}
        showImages={false}
        showPrompts={false}
        showLLMConfig={false}
      />,
    );
    expect(html.includes("对话模型:")).toBe(true);
    expect(html.includes("平台默认")).toBe(true);
  });
});
