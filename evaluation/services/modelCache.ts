/**
 * 模型缓存服务
 * 提供OpenRouter模型列表的缓存功能
 */

import api from "./api";
import type { OpenRouterModel, ScoringModel } from "../types";

// 缓存配置
const CACHE_KEYS = {
  OPENROUTER_MODELS: "inty_openrouter_models_cache",
  OPENROUTER_MODELS_TIME: "inty_openrouter_models_cache_time",
  SCORING_MODELS: "inty_scoring_models_cache",
  SCORING_MODELS_TIME: "inty_scoring_models_cache_time",
};

const CACHE_EXPIRY = 60 * 60 * 1000; // 1小时过期

class ModelCacheService {
  /**
   * 获取OpenRouter模型列表（带缓存）
   */
  async getOpenRouterModels(forceRefresh = false): Promise<OpenRouterModel[]> {
    // 检查缓存
    if (!forceRefresh) {
      const cached = this.getCachedModels(
        CACHE_KEYS.OPENROUTER_MODELS,
        CACHE_KEYS.OPENROUTER_MODELS_TIME,
      );
      if (cached) {
        console.log(`使用缓存的OpenRouter模型列表: ${cached.length} 个模型`);
        return cached;
      }
    }

    try {
      console.log("从OpenRouter API获取完整模型列表");
      const models = await api.scoring.getOpenRouterModels();

      // 缓存API结果
      this.cacheModels(
        models,
        CACHE_KEYS.OPENROUTER_MODELS,
        CACHE_KEYS.OPENROUTER_MODELS_TIME,
      );
      console.log(`成功获取并缓存OpenRouter模型列表: ${models.length} 个模型`);
      return models;
    } catch (error) {
      console.warn("OpenRouter API调用失败，使用默认模型列表:", error);

      // API失败时使用默认模型列表
      const defaultModels = this.getDefaultOpenRouterModels();
      console.log(`使用默认模型列表: ${defaultModels.length} 个模型`);
      return defaultModels;
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
   * 清除OpenRouter模型缓存
   */
  clearOpenRouterCache(): void {
    localStorage.removeItem(CACHE_KEYS.OPENROUTER_MODELS);
    localStorage.removeItem(CACHE_KEYS.OPENROUTER_MODELS_TIME);
    console.log("已清除OpenRouter模型缓存");
  }

  /**
   * 强制刷新OpenRouter模型列表
   */
  async refreshOpenRouterModels(): Promise<OpenRouterModel[]> {
    console.log("强制刷新OpenRouter模型列表");
    this.clearOpenRouterCache();
    return await this.getOpenRouterModels(true);
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
    const openRouterCacheTime = localStorage.getItem(
      CACHE_KEYS.OPENROUTER_MODELS_TIME,
    );
    const scoringCacheTime = localStorage.getItem(
      CACHE_KEYS.SCORING_MODELS_TIME,
    );

    return {
      openRouter: {
        hasCache: !!openRouterCacheTime,
        cacheTime: openRouterCacheTime
          ? new Date(parseInt(openRouterCacheTime))
          : null,
        isExpired: openRouterCacheTime
          ? Date.now() - parseInt(openRouterCacheTime) > CACHE_EXPIRY
          : true,
      },
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
  ): any[] | null {
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
  private cacheModels(models: any[], cacheKey: string, timeKey: string): void {
    try {
      localStorage.setItem(cacheKey, JSON.stringify(models));
      localStorage.setItem(timeKey, Date.now().toString());
    } catch (error) {
      console.error("缓存模型列表失败:", error);
    }
  }

  /**
   * 获取默认OpenRouter模型列表 - 包含更多真实模型
   */
  private getDefaultOpenRouterModels(): OpenRouterModel[] {
    return [
      // OpenAI 模型
      {
        id: "openai/gpt-4o",
        name: "GPT-4o",
        description: "OpenAI最新的多模态模型，支持文本、图像、音频和视频处理",
      },
      {
        id: "openai/gpt-4o-mini",
        name: "GPT-4o Mini",
        description: "OpenAI的轻量级多模态模型，快速且经济",
      },
      {
        id: "openai/gpt-4-turbo",
        name: "GPT-4 Turbo",
        description: "OpenAI的GPT-4增强版本，更快的推理速度",
      },
      {
        id: "openai/gpt-4",
        name: "GPT-4",
        description: "OpenAI的高性能大语言模型",
      },
      {
        id: "openai/gpt-3.5-turbo",
        name: "GPT-3.5 Turbo",
        description: "OpenAI优化的对话模型，高效且实用",
      },
      {
        id: "openai/gpt-3.5-turbo-16k",
        name: "GPT-3.5 Turbo 16K",
        description: "支持16K上下文的GPT-3.5 Turbo",
      },

      // Anthropic 模型
      {
        id: "anthropic/claude-3.5-sonnet",
        name: "Claude 3.5 Sonnet",
        description: "Anthropic的最新Claude模型，擅长分析、写作和推理",
      },
      {
        id: "anthropic/claude-3.5-haiku",
        name: "Claude 3.5 Haiku",
        description: "Anthropic的快速模型，适合实时对话",
      },
      {
        id: "anthropic/claude-3-opus",
        name: "Claude 3 Opus",
        description: "Anthropic的旗舰模型，最强的推理和创作能力",
      },
      {
        id: "anthropic/claude-3-sonnet",
        name: "Claude 3 Sonnet",
        description: "平衡性能和速度的Claude 3模型",
      },
      {
        id: "anthropic/claude-3-haiku",
        name: "Claude 3 Haiku",
        description: "最快的Claude 3模型",
      },

      // Google 模型
      {
        id: "google/gemini-pro-1.5",
        name: "Gemini Pro 1.5",
        description: "Google的Gemini模型，支持长上下文和多模态",
      },
      {
        id: "google/gemini-pro",
        name: "Gemini Pro",
        description: "Google的高性能语言模型",
      },
      {
        id: "google/gemini-flash-1.5",
        name: "Gemini Flash 1.5",
        description: "Google的快速响应模型",
      },

      // Meta Llama 模型
      {
        id: "meta-llama/llama-3.1-405b-instruct",
        name: "Llama 3.1 405B Instruct",
        description: "Meta最大的开源语言模型，顶级性能",
      },
      {
        id: "meta-llama/llama-3.1-70b-instruct",
        name: "Llama 3.1 70B Instruct",
        description: "Meta的中型语言模型，平衡性能和效率",
      },
      {
        id: "meta-llama/llama-3.1-8b-instruct",
        name: "Llama 3.1 8B Instruct",
        description: "Meta的小型语言模型，快速响应",
      },
      {
        id: "meta-llama/llama-3-70b-instruct",
        name: "Llama 3 70B Instruct",
        description: "Meta Llama 3的70B指令优化版本",
      },
      {
        id: "meta-llama/llama-3-8b-instruct",
        name: "Llama 3 8B Instruct",
        description: "Meta Llama 3的8B指令优化版本",
      },

      // Mistral AI 模型
      {
        id: "mistralai/mistral-large",
        name: "Mistral Large",
        description: "Mistral AI的大型语言模型",
      },
      {
        id: "mistralai/mistral-medium",
        name: "Mistral Medium",
        description: "Mistral AI的中型语言模型",
      },
      {
        id: "mistralai/mistral-small",
        name: "Mistral Small",
        description: "Mistral AI的小型语言模型",
      },
      {
        id: "mistralai/mixtral-8x7b-instruct",
        name: "Mixtral 8x7B Instruct",
        description: "Mistral AI的混合专家模型",
      },
      {
        id: "mistralai/mistral-7b-instruct",
        name: "Mistral 7B Instruct",
        description: "Mistral AI的7B指令跟随模型",
      },

      // Cohere 模型
      {
        id: "cohere/command-r-plus",
        name: "Command R+",
        description: "Cohere的增强版对话模型",
      },
      {
        id: "cohere/command-r",
        name: "Command R",
        description: "Cohere的对话和RAG优化模型",
      },

      // Perplexity 模型
      {
        id: "perplexity/llama-3.1-sonar-large-128k-online",
        name: "Perplexity Sonar Large 128K Online",
        description: "Perplexity的在线搜索增强模型",
      },
      {
        id: "perplexity/llama-3.1-sonar-small-128k-online",
        name: "Perplexity Sonar Small 128K Online",
        description: "Perplexity的轻量级在线搜索模型",
      },

      // 其他热门模型
      {
        id: "deepseek/deepseek-chat",
        name: "DeepSeek Chat",
        description: "DeepSeek的对话优化模型",
      },
      {
        id: "qwen/qwen-2-72b-instruct",
        name: "Qwen 2 72B Instruct",
        description: "阿里巴巴的Qwen 2大型语言模型",
      },
      {
        id: "microsoft/wizardlm-2-8x22b",
        name: "WizardLM 2 8x22B",
        description: "Microsoft的WizardLM 2混合专家模型",
      },
      {
        id: "databricks/dbrx-instruct",
        name: "DBRX Instruct",
        description: "Databricks的开源混合专家模型",
      },
      {
        id: "01-ai/yi-large",
        name: "Yi Large",
        description: "零一万物的大型语言模型",
      },
      {
        id: "nvidia/nemotron-4-340b-instruct",
        name: "Nemotron 4 340B Instruct",
        description: "NVIDIA的大型指令跟随模型",
      },

      // 更多流行的OpenRouter模型
      {
        id: "anthropic/claude-2",
        name: "Claude 2",
        description: "Anthropic的Claude 2模型",
      },
      {
        id: "anthropic/claude-2.1",
        name: "Claude 2.1",
        description: "Anthropic的Claude 2.1增强版本",
      },
      {
        id: "anthropic/claude-instant-1.2",
        name: "Claude Instant 1.2",
        description: "Anthropic的快速响应模型",
      },
      {
        id: "openai/gpt-4-1106-preview",
        name: "GPT-4 Turbo Preview",
        description: "OpenAI GPT-4 Turbo的预览版本",
      },
      {
        id: "openai/gpt-4-vision-preview",
        name: "GPT-4 Vision Preview",
        description: "OpenAI的视觉理解模型",
      },
      {
        id: "google/palm-2-chat-bison",
        name: "PaLM 2 Chat Bison",
        description: "Google的PaLM 2对话模型",
      },
      {
        id: "google/palm-2-codechat-bison",
        name: "PaLM 2 CodeChat Bison",
        description: "Google的PaLM 2代码对话模型",
      },
      {
        id: "huggingface/starcoder",
        name: "StarCoder",
        description: "HuggingFace的代码生成模型",
      },
      {
        id: "togethercomputer/redpajama-incite-7b-chat",
        name: "RedPajama INCITE 7B Chat",
        description: "TogetherAI的对话优化模型",
      },
      {
        id: "nousresearch/nous-hermes-llama2-13b",
        name: "Nous Hermes Llama2 13B",
        description: "NousResearch的Hermes模型",
      },
      {
        id: "gryphe/mythomist-7b",
        name: "Mythomist 7B",
        description: "Gryphe的创意写作优化模型",
      },
      {
        id: "openchat/openchat-7b",
        name: "OpenChat 7B",
        description: "OpenChat的对话模型",
      },
      {
        id: "teknium/openhermes-2.5-mistral-7b",
        name: "OpenHermes 2.5 Mistral 7B",
        description: "Teknium的OpenHermes模型",
      },
      {
        id: "undi95/toppy-m-7b",
        name: "Toppy M 7B",
        description: "Undi95的创意写作模型",
      },
      {
        id: "jondurbin/airoboros-l2-70b",
        name: "Airoboros L2 70B",
        description: "Jondurbin的指令跟随模型",
      },
      {
        id: "phind/phind-codellama-34b",
        name: "Phind CodeLlama 34B",
        description: "Phind的代码专用模型",
      },
      {
        id: "wizardlm/wizardlm-70b",
        name: "WizardLM 70B",
        description: "WizardLM的大型指令跟随模型",
      },
      {
        id: "alpaca/alpaca-7b",
        name: "Alpaca 7B",
        description: "Stanford的Alpaca指令跟随模型",
      },
      {
        id: "vicuna/vicuna-13b",
        name: "Vicuna 13B",
        description: "UC Berkeley的Vicuna对话模型",
      },
      {
        id: "rwkv/rwkv-4-raven-14b",
        name: "RWKV 4 Raven 14B",
        description: "RWKV的高效语言模型",
      },
      {
        id: "pygmalionai/mythalion-13b",
        name: "Mythalion 13B",
        description: "PygmalionAI的角色扮演模型",
      },
      {
        id: "neversleep/noromaid-mixtral-8x7b-instruct",
        name: "Noromaid Mixtral 8x7B Instruct",
        description: "NeverSleep的创意写作模型",
      },
      {
        id: "lizpreciatior/lzlv-70b-fp16-hf",
        name: "LZLV 70B",
        description: "LizPreciatior的高质量语言模型",
      },
      {
        id: "austism/chronos-hermes-13b",
        name: "Chronos Hermes 13B",
        description: "Austism的时间感知对话模型",
      },
      {
        id: "cognitivecomputations/dolphin-mixtral-8x7b",
        name: "Dolphin Mixtral 8x7B",
        description: "Cognitive Computations的无审查模型",
      },
    ];
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
