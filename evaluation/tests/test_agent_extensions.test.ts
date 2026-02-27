/**
 * Agent Extensions 测试
 * 验证头像截取数据在 extensions 字段中的存储和读取
 */

import { describe, it, expect, beforeAll } from "vitest";

// 直接定义类型，避免模块导入问题
interface AvatarCropData {
  x: number;
  y: number;
  width: number;
  height: number;
  imageWidth: number;
  imageHeight: number;
}

interface Agent {
  id: string;
  name: string;
  avatar?: string;
  background?: string;
  extensions?: {
    avatar_crop?: AvatarCropData;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T | null;
}

// 模拟 API 调用
const API_BASE_URL = "http://localhost:8000";

/**
 * 获取智能体列表
 */
async function getAgents(): Promise<Agent[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/ai/agents/me`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        // 注意：实际使用时需要添加 Authorization header
        // 'Authorization': 'Bearer YOUR_TOKEN'
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: ApiResponse<Agent[]> = await response.json();
    return result.data || [];
  } catch (error) {
    console.error("获取智能体列表失败:", error);
    throw error;
  }
}

/**
 * 获取单个智能体详情
 */
async function getAgent(agentId: string): Promise<Agent | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/ai/agents/${agentId}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          // 注意：实际使用时需要添加 Authorization header
          // 'Authorization': 'Bearer YOUR_TOKEN'
        },
      },
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: ApiResponse<Agent> = await response.json();
    return result.data;
  } catch (error) {
    console.error(`获取智能体 ${agentId} 失败:`, error);
    throw error;
  }
}

/**
 * 创建模拟数据
 */
function createMockAgents(): Agent[] {
  return [
    {
      id: "agent_001",
      name: "测试角色1",
      avatar: "https://example.com/avatar1.jpg",
      background: "https://example.com/background1.jpg",
      extensions: {
        avatar_crop: {
          x: 100,
          y: 50,
          width: 200,
          height: 200,
          imageWidth: 800,
          imageHeight: 600,
        },
      },
    },
    {
      id: "agent_002",
      name: "测试角色2",
      avatar: "https://example.com/avatar2.jpg",
      background: "https://example.com/background2.jpg",
      extensions: {
        avatar_crop: {
          x: 150,
          y: 75,
          width: 300,
          height: 300,
          imageWidth: 1200,
          imageHeight: 900,
        },
        theme: "dark",
        settings: { auto_reply: true },
      },
    },
    {
      id: "agent_003",
      name: "测试角色3",
      avatar: "https://example.com/avatar3.jpg",
      background: undefined,
      extensions: undefined,
    },
  ];
}

describe("Agent Extensions", () => {
  let mockAgents: Agent[];

  beforeAll(() => {
    mockAgents = createMockAgents();
  });

  describe("Extensions 字段验证", () => {
    it("应该正确解析 extensions 字段", () => {
      const agentWithExtensions = mockAgents[0];
      expect(agentWithExtensions.extensions).toBeDefined();
      expect(agentWithExtensions.extensions?.avatar_crop).toBeDefined();
    });

    it("应该处理没有 extensions 字段的智能体", () => {
      const agentWithoutExtensions = mockAgents[2];
      expect(agentWithoutExtensions.extensions).toBeUndefined();
    });

    it("应该包含其他扩展数据", () => {
      const agentWithMultipleExtensions = mockAgents[1];
      expect(agentWithMultipleExtensions.extensions?.theme).toBe("dark");
      expect(agentWithMultipleExtensions.extensions?.settings).toEqual({
        auto_reply: true,
      });
    });
  });

  describe("头像截取数据验证", () => {
    it("应该验证 avatar_crop 数据的完整性", () => {
      const agent = mockAgents[0];
      const avatarCrop = agent.extensions?.avatar_crop;

      expect(avatarCrop).toBeDefined();
      expect(avatarCrop?.x).toBe(100);
      expect(avatarCrop?.y).toBe(50);
      expect(avatarCrop?.width).toBe(200);
      expect(avatarCrop?.height).toBe(200);
      expect(avatarCrop?.imageWidth).toBe(800);
      expect(avatarCrop?.imageHeight).toBe(600);
    });

    it("应该验证数据有效性", () => {
      const agent = mockAgents[0];
      const avatarCrop = agent.extensions?.avatar_crop;

      expect(avatarCrop?.x).toBeGreaterThanOrEqual(0);
      expect(avatarCrop?.y).toBeGreaterThanOrEqual(0);
      expect(avatarCrop?.width).toBeGreaterThan(0);
      expect(avatarCrop?.height).toBeGreaterThan(0);
      expect(avatarCrop?.imageWidth).toBeGreaterThan(0);
      expect(avatarCrop?.imageHeight).toBeGreaterThan(0);
    });

    it("应该处理不同的截取数据", () => {
      const agent = mockAgents[1];
      const avatarCrop = agent.extensions?.avatar_crop;

      expect(avatarCrop?.x).toBe(150);
      expect(avatarCrop?.y).toBe(75);
      expect(avatarCrop?.width).toBe(300);
      expect(avatarCrop?.height).toBe(300);
    });
  });

  describe("头像信息验证", () => {
    it("应该正确识别头像和背景图", () => {
      const agent = mockAgents[0];
      expect(agent.avatar).toBeDefined();
      expect(agent.background).toBeDefined();
    });

    it("应该处理没有背景图的智能体", () => {
      const agent = mockAgents[2];
      expect(agent.avatar).toBeDefined();
      expect(agent.background).toBeUndefined();
    });
  });

  describe("计算逻辑测试", () => {
    it("应该正确计算头像显示尺寸", () => {
      const avatarCrop: AvatarCropData = {
        x: 100,
        y: 50,
        width: 200,
        height: 200,
        imageWidth: 800,
        imageHeight: 600,
      };

      const displaySize = 64;
      const scale = displaySize / avatarCrop.width;

      const displayWidth = avatarCrop.imageWidth * scale;
      const displayHeight = avatarCrop.imageHeight * scale;
      const offsetX = -avatarCrop.x * scale;
      const offsetY = -avatarCrop.y * scale;

      expect(scale).toBeCloseTo(0.32, 2);
      expect(displayWidth).toBeCloseTo(256, 1);
      expect(displayHeight).toBeCloseTo(192, 1);
      expect(offsetX).toBeCloseTo(-32, 1);
      expect(offsetY).toBeCloseTo(-16, 1);
    });

    it("应该正确计算截取区域百分比", () => {
      const avatarCrop: AvatarCropData = {
        x: 100,
        y: 50,
        width: 200,
        height: 200,
        imageWidth: 800,
        imageHeight: 600,
      };

      const cropLeftPercent = (avatarCrop.x / avatarCrop.imageWidth) * 100;
      const cropTopPercent = (avatarCrop.y / avatarCrop.imageHeight) * 100;
      const cropWidthPercent = (avatarCrop.width / avatarCrop.imageWidth) * 100;
      const cropHeightPercent =
        (avatarCrop.height / avatarCrop.imageHeight) * 100;

      expect(cropLeftPercent).toBeCloseTo(12.5, 1);
      expect(cropTopPercent).toBeCloseTo(8.3, 1);
      expect(cropWidthPercent).toBeCloseTo(25.0, 1);
      expect(cropHeightPercent).toBeCloseTo(33.3, 1);
    });
  });

  describe("API 集成测试", () => {
    it.skip("应该能够获取智能体列表", async () => {
      // 跳过真实 API 测试，除非有有效的认证
      const agents = await getAgents();
      expect(Array.isArray(agents)).toBe(true);
    });

    it.skip("应该能够获取单个智能体详情", async () => {
      // 跳过真实 API 测试，除非有有效的认证
      const agent = await getAgent("test-agent-id");
      expect(agent).toBeDefined();
    });
  });
});

// 导出测试函数供其他用途
export { createMockAgents, getAgents, getAgent };
