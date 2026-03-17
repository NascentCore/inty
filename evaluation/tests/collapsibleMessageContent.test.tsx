import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CollapsibleMessageContent } from "../components/CollapsibleMessageContent";

describe("CollapsibleMessageContent", () => {
  it("shows placeholder when content is empty", () => {
    render(<CollapsibleMessageContent content={null} />);

    expect(screen.getByText("[无文本内容]")).toBeTruthy();
  });

  it("renders message content with ellipsis typography", () => {
    const longContent = "这是一个很长的消息内容".repeat(50);
    const previewContent = longContent.slice(0, 12);
    const { container } = render(
      <CollapsibleMessageContent content={`  ${longContent}  `} />,
    );

    expect(screen.getByText(previewContent, { exact: false })).toBeTruthy();
    expect(screen.queryByText("[无文本内容]")).toBeNull();
    expect(container.querySelector(".ant-typography-ellipsis")).not.toBeNull();
  });
});
