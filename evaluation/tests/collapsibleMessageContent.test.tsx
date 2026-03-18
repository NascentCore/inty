import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CollapsibleMessageContent } from "../components/CollapsibleMessageContent";

describe("CollapsibleMessageContent", () => {
  it("shows placeholder when content is empty", () => {
    const html = renderToStaticMarkup(
      <CollapsibleMessageContent content={null} />,
    );
    expect(html.includes("[无文本内容]")).toBe(true);
  });

  it("renders message content with ellipsis typography", () => {
    const longContent = "这是一个很长的消息内容".repeat(50);
    const html = renderToStaticMarkup(
      <CollapsibleMessageContent content={`  ${longContent}  `} />,
    );

    expect(html.includes(longContent.slice(0, 24))).toBe(true);
    expect(html.includes("[无文本内容]")).toBe(false);
    expect(html.includes("ant-typography")).toBe(true);
  });
});
