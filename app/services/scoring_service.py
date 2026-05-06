"""Scores agent responses with an external LLM and parses fallback results.

This service builds scoring prompts, calls the configured evaluation model, and
normalizes model output into score fields used by evaluation workflows.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import global_config_loaded_from_config_yaml

from loguru import logger


class ScoringService:
    """评分服务 - 使用外部LLM对智能体回复进行评分"""

    def __init__(self):
        # 从配置文件读取OpenRouter配置
        self.openrouter_base_url = global_config_loaded_from_config_yaml.agent.base_url
        self.openrouter_api_key = global_config_loaded_from_config_yaml.agent.api_key

    async def score_response(
        self,
        question: str,
        agent_response: str,
        agent_info: Dict[str, Any],
        scoring_model: str,
        scoring_criteria: str,
    ) -> Dict[str, Any]:
        """对智能体回复进行评分"""

        try:
            # 构建评分提示词
            scoring_prompt = self._build_scoring_prompt(
                question=question,
                agent_response=agent_response,
                agent_info=agent_info,
                scoring_criteria=scoring_criteria,
            )

            # 调用评分模型
            llm_response = await self._call_scoring_model(
                model=scoring_model, prompt=scoring_prompt
            )

            if not llm_response:
                return {"success": False, "error": "Scoring model call failed"}

            # 解析评分结果
            scoring_result = self._parse_scoring_response(llm_response)

            return {
                "success": True,
                "overall_score": scoring_result.get("overall_score"),
                "detailed_scores": scoring_result.get("detailed_scores"),
                "reason": scoring_result.get("reason"),
                "raw_response": llm_response,
            }

        except Exception as e:
            logger.error(f"评分失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _build_scoring_prompt(
        self,
        question: str,
        agent_response: str,
        agent_info: Dict[str, Any],
        scoring_criteria: str,
    ) -> str:
        """构建评分提示词"""

        agent_name = agent_info.get("name", "智能体")
        agent_intro = agent_info.get("intro", "")
        agent_personality = agent_info.get("personality", "")

        prompt = f"""你是一个专业的AI智能体评测专家，请根据以下标准对智能体的回复进行客观评分。

# 智能体信息
**名称**: {agent_name}
**简介**: {agent_intro}
**角色设定**: {agent_personality}

# 测试问题
{question}

# 智能体回复
{agent_response}

# 评分标准
{scoring_criteria}

# 评分要求
请严格按照以下JSON格式输出评分结果，不要添加任何其他内容：

```json
{{
    "overall_score": 8.5,
    "detailed_scores": {{
        "角色一致性": 9.0,
        "表达自然度": 8.0,
        "情境适应性": 8.5,
        "创意表现力": 9.0
    }},
    "reason": "详细的评分理由，解释各个维度的得分原因..."
}}
```

请确保评分客观公正，理由详细具体。"""

        return prompt

    async def _call_scoring_model(self, model: str, prompt: str) -> Optional[str]:
        """调用评分模型"""

        # 这里应该根据model参数选择不同的API
        # 暂时实现OpenRouter调用逻辑

        if not self.openrouter_api_key:
            logger.warning("OpenRouter API Key未配置，使用模拟评分")
            return await self._mock_scoring_response(prompt)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://inty.ai",
                    "X-Title": "InTy Evaluation System",
                }

                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                }

                response = await client.post(
                    f"{self.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=data,
                )

                if response.status_code != 200:
                    logger.error(
                        f"OpenRouter API调用失败: {response.status_code} - {response.text}"
                    )
                    return None

                result = response.json()
                content = (
                    result.get("choices", [{}])[0].get("message", {}).get("content", "")
                )

                return content

        except Exception as e:
            logger.error(f"调用评分模型失败: {str(e)}")
            return None

    async def _mock_scoring_response(self, prompt: str) -> str:
        """模拟评分响应 - 用于开发测试"""

        # 简单的模拟逻辑，实际应该移除
        await asyncio.sleep(1)  # 模拟API调用延迟

        mock_response = {
            "overall_score": 8.2,
            "detailed_scores": {
                "角色一致性": 8.5,
                "表达自然度": 7.8,
                "情境适应性": 8.0,
                "创意表现力": 8.5,
            },
            "reason": "智能体能够很好地保持角色设定，回复自然流畅，对问题情境有适当的理解和回应，表现出一定的创意性。建议在情境适应性方面可以更加细致。",
        }

        return (
            f"```json\n{json.dumps(mock_response, ensure_ascii=False, indent=2)}\n```"
        )

    def _parse_scoring_response(self, response: str) -> Dict[str, Any]:
        """解析评分响应"""

        try:
            # 提取JSON部分
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个响应
                json_str = response.strip()

            # 解析JSON
            result = json.loads(json_str)

            # 验证必要字段
            if "overall_score" not in result:
                raise ValueError("Missing overall_score field")

            # 确保分数在有效范围内
            overall_score = float(result["overall_score"])
            if not (0 <= overall_score <= 10):
                overall_score = max(0, min(10, overall_score))
                result["overall_score"] = overall_score

            # 处理详细评分
            detailed_scores = result.get("detailed_scores", {})
            for dimension, score in detailed_scores.items():
                if isinstance(score, (int, float)):
                    detailed_scores[dimension] = max(0, min(10, float(score)))

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}, 响应内容: {response[:500]}")
            return self._fallback_scoring(response)

        except Exception as e:
            logger.error(f"评分解析失败: {str(e)}")
            return self._fallback_scoring(response)

    def _fallback_scoring(self, response: str) -> Dict[str, Any]:
        """备用评分解析 - 当JSON解析失败时"""

        # 尝试提取数字分数
        scores = re.findall(r"(\d+(?:\.\d+)?)", response)
        if scores:
            try:
                overall_score = float(scores[0])
                overall_score = max(0, min(10, overall_score))

                return {
                    "overall_score": overall_score,
                    "detailed_scores": {},
                    "reason": "Scoring parse failed; using extracted numeric score",
                }
            except (OverflowError, TypeError, ValueError):
                pass

        # 完全失败时的默认分数
        return {
            "overall_score": 5.0,
            "detailed_scores": {},
            "reason": (
                "Scoring parse failed; using default score. "
                f"Raw response: {response[:200]}..."
            ),
        }

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用的评分模型列表"""

        # 直接返回默认模型列表，避免网络请求延迟
        # 如果需要实时获取OpenRouter模型，可以在后台异步更新
        logger.debug("返回默认评分模型列表")

        return [
            {
                "id": "meta-llama/llama-3.1-405b-instruct",
                "name": "Llama 3.1 405B Instruct",
                "description": "Meta最新的大型语言模型，适合复杂的推理和评估任务",
                "context_length": 32768,
                "provider": "Meta",
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "description": "Anthropic的Claude模型，擅长分析和评估",
                "context_length": 200000,
                "provider": "Anthropic",
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "description": "OpenAI的多模态模型，具有强大的理解能力",
                "context_length": 128000,
                "provider": "OpenAI",
            },
            {
                "id": "google/gemini-pro-1.5",
                "name": "Gemini Pro 1.5",
                "description": "Google的Gemini模型，支持长上下文",
                "context_length": 2000000,
                "provider": "Google",
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "description": "OpenAI的轻量级模型，快速且经济",
                "context_length": 128000,
                "provider": "OpenAI",
            },
            {
                "id": "anthropic/claude-3.5-haiku",
                "name": "Claude 3.5 Haiku",
                "description": "Anthropic的快速模型，适合简单评估任务",
                "context_length": 200000,
                "provider": "Anthropic",
            },
        ]

    async def _fetch_openrouter_models(self) -> List[Dict[str, Any]]:
        """从OpenRouter API获取模型列表"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://inty.ai",
                    "X-Title": "InTy Evaluation System",
                }

                logger.debug("正在从OpenRouter API获取模型列表...")
                response = await client.get(
                    "https://openrouter.ai/api/v1/models", headers=headers
                )

                if response.status_code != 200:
                    logger.error(
                        f"OpenRouter API调用失败: {response.status_code} - {response.text}"
                    )
                    return self._get_default_openrouter_models()

                result = response.json()
                models_data = result.get("data", [])

                logger.debug(f"OpenRouter API返回了 {len(models_data)} 个模型")

                # 转换为我们需要的格式，显示所有模型供用户选择
                all_models = []
                for model in models_data:
                    model_id = model.get("id", "")

                    # 不过滤，显示所有模型
                    all_models.append(
                        {
                            "id": model_id,
                            "name": model.get("name", model_id),
                            "description": model.get("description", ""),
                            "context_length": model.get("context_length", 0),
                            "provider": self._extract_provider(model_id),
                        }
                    )

                # 按质量和受欢迎程度排序，优先显示高质量模型
                all_models.sort(key=lambda m: self._model_priority(m["id"]))

                logger.debug(f"成功处理 {len(all_models)} 个OpenRouter模型")
                return all_models

        except Exception as e:
            logger.error(f"获取OpenRouter模型失败: {str(e)}")
            return self._get_default_openrouter_models()

    def _get_default_openrouter_models(self) -> List[Dict[str, Any]]:
        """获取默认的OpenRouter模型列表"""
        logger.debug("使用默认的OpenRouter模型列表")

        return [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "description": "OpenAI最新的多模态模型，支持文本、图像、音频和视频处理",
                "context_length": 128000,
                "provider": "OpenAI",
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "description": "OpenAI的轻量级多模态模型，快速且经济",
                "context_length": 128000,
                "provider": "OpenAI",
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "description": "Anthropic的最新Claude模型，擅长分析、写作和推理",
                "context_length": 200000,
                "provider": "Anthropic",
            },
            {
                "id": "anthropic/claude-3.5-haiku",
                "name": "Claude 3.5 Haiku",
                "description": "Anthropic的快速模型，适合实时对话",
                "context_length": 200000,
                "provider": "Anthropic",
            },
            {
                "id": "anthropic/claude-3-opus",
                "name": "Claude 3 Opus",
                "description": "Anthropic的旗舰模型，最强的推理和创作能力",
                "context_length": 200000,
                "provider": "Anthropic",
            },
            {
                "id": "google/gemini-pro-1.5",
                "name": "Gemini Pro 1.5",
                "description": "Google的Gemini模型，支持长上下文和多模态",
                "context_length": 2000000,
                "provider": "Google",
            },
            {
                "id": "meta-llama/llama-3.1-405b-instruct",
                "name": "Llama 3.1 405B Instruct",
                "description": "Meta最大的开源语言模型，顶级性能",
                "context_length": 32768,
                "provider": "Meta",
            },
            {
                "id": "meta-llama/llama-3.1-70b-instruct",
                "name": "Llama 3.1 70B Instruct",
                "description": "Meta的中型语言模型，平衡性能和效率",
                "context_length": 32768,
                "provider": "Meta",
            },
            {
                "id": "mistralai/mixtral-8x7b-instruct",
                "name": "Mixtral 8x7B Instruct",
                "description": "Mistral AI的混合专家模型",
                "context_length": 32768,
                "provider": "Mistral AI",
            },
            {
                "id": "deepseek/deepseek-chat",
                "name": "DeepSeek Chat",
                "description": "DeepSeek的对话优化模型",
                "context_length": 32768,
                "provider": "DeepSeek",
            },
            {
                "id": "perplexity/llama-3.1-sonar-large-128k-online",
                "name": "Perplexity Sonar Large 128K Online",
                "description": "Perplexity的在线搜索增强模型",
                "context_length": 131072,
                "provider": "Perplexity",
            },
            {
                "id": "qwen/qwen-2-72b-instruct",
                "name": "Qwen 2 72B Instruct",
                "description": "阿里巴巴的Qwen 2大型语言模型",
                "context_length": 131072,
                "provider": "Alibaba",
            },
        ]

    def _is_suitable_for_evaluation(self, model: Dict[str, Any]) -> bool:
        """判断模型是否适合用于评测"""

        model_id = model.get("id", "").lower()

        # 包含这些关键词的模型通常适合评测
        suitable_keywords = [
            "gpt-4",
            "claude",
            "gemini",
            "llama",
            "mixtral",
            "command",
            "mistral",
            "qwen",
            "deepseek",
        ]

        # 排除这些类型的模型
        excluded_keywords = [
            "vision",
            "embedding",
            "whisper",
            "tts",
            "image",
            "code",
            "free",
            "beta",
            "preview",
        ]

        # 检查是否包含适合的关键词
        has_suitable = any(keyword in model_id for keyword in suitable_keywords)

        # 检查是否包含排除的关键词
        has_excluded = any(keyword in model_id for keyword in excluded_keywords)

        return has_suitable and not has_excluded

    def _extract_provider(self, model_id: str) -> str:
        """从模型ID提取提供商"""

        if model_id.startswith("openai/"):
            return "OpenAI"
        elif model_id.startswith("anthropic/"):
            return "Anthropic"
        elif model_id.startswith("google/"):
            return "Google"
        elif model_id.startswith("meta-llama/"):
            return "Meta"
        elif model_id.startswith("mistralai/"):
            return "Mistral AI"
        elif model_id.startswith("01-ai/"):
            return "01.AI"
        elif model_id.startswith("qwen/"):
            return "Alibaba"
        elif model_id.startswith("deepseek/"):
            return "DeepSeek"
        else:
            return "Other"

    def _model_priority(self, model_id: str) -> int:
        """模型优先级排序（越小越优先）"""

        # 定义优先级模型
        priority_models = [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "meta-llama/llama-3.1-405b-instruct",
            "google/gemini-pro-1.5",
            "anthropic/claude-3.5-haiku",
            "openai/gpt-4o-mini",
            "mistralai/mistral-large-2407",
        ]

        try:
            return priority_models.index(model_id)
        except ValueError:
            return 999  # 不在优先级列表中的模型排在后面

    def validate_scoring_criteria(self, criteria: str) -> Dict[str, Any]:
        """验证评分标准的有效性"""

        issues = []
        suggestions = []

        if len(criteria.strip()) < 50:
            issues.append(
                "Scoring criteria is too short; consider providing more detailed guidance"
            )

        if "分" not in criteria and "评" not in criteria:
            issues.append("Scoring criteria should explicitly mention scoring terms")

        if not re.search(r"\d+.*分", criteria):
            suggestions.append(
                "Consider specifying a score range in the criteria, e.g., '1-10'"
            )

        if "维度" not in criteria and "方面" not in criteria:
            suggestions.append("Consider specifying scoring dimensions in the criteria")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
        }
