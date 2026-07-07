/**
 * 模型缓存服务
 * 提供评分模型列表的缓存功能，OpenRouter模型列表不缓存
 */

import api from "./api";
import type { OpenRouterModel, ScoringModel } from "../types";

// 缓存配置
const CACHE_KEYS = {
  SCORING_MODELS: "inty_scoring_models_cache",
  SCORING_MODELS_TIME: "inty_scoring_models_cache_time",
};

const CACHE_EXPIRY = 60 * 60 * 1000; // 1小时过期

class ModelCacheService {
  /**
   * 获取OpenRouter模型列表（无缓存）
   */
  async getOpenRouterModels(): Promise<OpenRouterModel[]> {
    try {
      console.log("从OpenRouter API获取模型列表");
      const models = await api.scoring.getOpenRouterModels();
      console.log(`成功获取OpenRouter模型列表: ${models.length} 个模型`);
      return models;
    } catch (error) {
      console.error("OpenRouter API调用失败:", error);
      throw error; // 重新抛出错误，让调用者处理
    }
  }

  /**
   * 获取评分模型列表（带缓存）
   */
  async getScoringModels(forceRefresh = false): Promise<ScoringModel[]> {
    try {
      // 检查缓存
      if (!forceRefresh) {
        const cached = this.getCachedModels(
          CACHE_KEYS.SCORING_MODELS,
          CACHE_KEYS.SCORING_MODELS_TIME,
        );
        if (cached) {
          console.log("使用缓存的评分模型列表");
          return cached;
        }
      }

      console.log("从API获取评分模型列表");

      // 从API获取
      const models = await api.scoring.getModels();

      // 缓存结果
      this.cacheModels(
        models,
        CACHE_KEYS.SCORING_MODELS,
        CACHE_KEYS.SCORING_MODELS_TIME,
      );

      return models;
    } catch (error) {
      console.error("获取评分模型列表失败:", error);

      // 尝试返回缓存的数据
      const cached = this.getCachedModels(
        CACHE_KEYS.SCORING_MODELS,
        CACHE_KEYS.SCORING_MODELS_TIME,
        true,
      );
      if (cached) {
        console.warn("API请求失败，使用过期的缓存数据");
        return cached;
      }

      // 返回默认模型列表
      return this.getDefaultScoringModels();
    }
  }

  /**
   * 清除所有模型缓存
   */
  clearAllCache(): void {
    Object.values(CACHE_KEYS).forEach((key) => {
      localStorage.removeItem(key);
    });
    console.log("已清除所有模型缓存");
  }

  /**
   * 清除评分模型缓存
   */
  clearScoringCache(): void {
    localStorage.removeItem(CACHE_KEYS.SCORING_MODELS);
    localStorage.removeItem(CACHE_KEYS.SCORING_MODELS_TIME);
    console.log("已清除评分模型缓存");
  }

  /**
   * 获取缓存状态信息
   */
  getCacheStatus() {
    const scoringCacheTime = localStorage.getItem(
      CACHE_KEYS.SCORING_MODELS_TIME,
    );

    return {
      scoring: {
        hasCache: !!scoringCacheTime,
        cacheTime: scoringCacheTime
          ? new Date(parseInt(scoringCacheTime))
          : null,
        isExpired: scoringCacheTime
          ? Date.now() - parseInt(scoringCacheTime) > CACHE_EXPIRY
          : true,
      },
    };
  }

  // 私有方法

  /**
   * 从缓存获取模型列表
   */
  private getCachedModels(
    cacheKey: string,
    timeKey: string,
    ignoreExpiry = false,
  ): ScoringModel[] | null {
    try {
      const cacheTime = localStorage.getItem(timeKey);
      const cachedData = localStorage.getItem(cacheKey);

      if (!cacheTime || !cachedData) {
        return null;
      }

      // 检查是否过期
      if (!ignoreExpiry && Date.now() - parseInt(cacheTime) > CACHE_EXPIRY) {
        return null;
      }

      return JSON.parse(cachedData);
    } catch (error) {
      console.error("读取缓存失败:", error);
      return null;
    }
  }

  /**
   * 缓存模型列表
   */
  private cacheModels(
    models: ScoringModel[],
    cacheKey: string,
    timeKey: string,
  ): void {
    try {
      localStorage.setItem(cacheKey, JSON.stringify(models));
      localStorage.setItem(timeKey, Date.now().toString());
    } catch (error) {
      console.error("缓存模型列表失败:", error);
    }
  }

  /**
   * 获取默认评分模型列表
   */
  private getDefaultScoringModels(): ScoringModel[] {
    return [
      {
        id: "meta-llama/llama-3.1-405b-instruct",
        name: "Llama 3.1 405B Instruct",
        description: "Meta最新的大型语言模型，适合复杂的推理和评估任务",
        context_length: 32768,
        provider: "Meta",
      },
      {
        id: "anthropic/claude-3.5-sonnet",
        name: "Claude 3.5 Sonnet",
        description: "Anthropic的Claude模型，擅长分析和评估",
        context_length: 200000,
        provider: "Anthropic",
      },
      {
        id: "openai/gpt-4o",
        name: "GPT-4o",
        description: "OpenAI的多模态模型，具有强大的理解能力",
        context_length: 128000,
        provider: "OpenAI",
      },
      {
        id: "google/gemini-pro-1.5",
        name: "Gemini Pro 1.5",
        description: "Google的Gemini模型，支持长上下文",
        context_length: 2000000,
        provider: "Google",
      },
      {
        id: "openai/gpt-4o-mini",
        name: "GPT-4o Mini",
        description: "OpenAI的轻量级模型，快速且经济",
        context_length: 128000,
        provider: "OpenAI",
      },
      {
        id: "anthropic/claude-3.5-haiku",
        name: "Claude 3.5 Haiku",
        description: "Anthropic的快速模型，适合简单评估任务",
        context_length: 200000,
        provider: "Anthropic",
      },
    ];
  }
}

// 导出单例实例
export const modelCacheService = new ModelCacheService();
export default modelCacheService;
