import { describe, expect, it } from "vitest";
import type { Agent } from "../types";
import { getAgentDetailModalActionKeys } from "../components/common/AgentDetailModal";

const buildAgent = (): Agent => ({
  id: "agent-1",
  name: "Brandy",
  visibility: "PUBLIC",
  gender: "FEMALE",
});

describe("getAgentDetailModalActionKeys", () => {
  it("没有智能体时仅返回关闭按钮", () => {
    expect(getAgentDetailModalActionKeys(null, false)).toEqual(["close"]);
    expect(getAgentDetailModalActionKeys(null, true)).toEqual(["close"]);
  });

  it("有智能体但不可编辑时仅返回关闭按钮", () => {
    expect(getAgentDetailModalActionKeys(buildAgent(), false)).toEqual([
      "close",
    ]);
  });

  it("有智能体且可编辑时返回关闭和编辑按钮", () => {
    expect(getAgentDetailModalActionKeys(buildAgent(), true)).toEqual([
      "close",
      "edit",
    ]);
  });
});
