#!/usr/bin/env python3
"""
AI Industry Weekly Report Generator

This script uses Google Custom Search API to find recent AI news from the past week
and then uses Gemini API to summarize the findings into a coherent report.

Prerequisites:
1. Google Custom Search JSON API key
2. Custom Search Engine (CSE) ID
3. Gemini API key

Environment variables required:
- GOOGLE_CSE_API_KEY: Your Google Custom Search API key
- GOOGLE_CSE_ID: Your Custom Search Engine ID
- GEMINI_API_KEY: Your Gemini API key

Optional:
- GEMINI_MODEL: Override the default Gemini model selection
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    import google.generativeai as genai
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print(
        "Please install with: pip install google-generativeai google-api-python-client"
    )
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]


class AIIndustryReporter:
    """Main class for generating AI industry weekly reports."""

    def __init__(self):
        """Initialize the reporter with API keys from environment variables."""
        self.google_api_key = os.getenv("GOOGLE_CSE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.custom_gemini_model = os.getenv("GEMINI_MODEL")

        if not all([self.google_api_key, self.google_cse_id, self.gemini_api_key]):
            missing_keys = []
            if not self.google_api_key:
                missing_keys.append("GOOGLE_CSE_API_KEY")
            if not self.google_cse_id:
                missing_keys.append("GOOGLE_CSE_ID")
            if not self.gemini_api_key:
                missing_keys.append("GEMINI_API_KEY")

            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_keys)}"
            )

        # Configure Gemini
        genai.configure(api_key=self.gemini_api_key)
        model_name = self._resolve_gemini_model()
        logger.info(f"Using Gemini model: {model_name}")
        self.gemini_model = genai.GenerativeModel(model_name)

        # Build Google Custom Search service
        self.search_service = build(
            "customsearch", "v1", developerKey=self.google_api_key
        )

    def _resolve_gemini_model(self) -> str:
        """
        Select a Gemini model that supports generateContent, honoring user override and
        falling back to default candidates when newer models are unavailable.
        """
        candidates = self._build_gemini_model_candidates()

        try:
            available_models = {
                self._normalize_model_name(model.name)
                for model in genai.list_models()
                if "generateContent" in getattr(model, "generation_methods", [])
            }
        except Exception as exc:
            logger.warning(
                "Failed to list Gemini models, falling back to preferred order: %s", exc
            )
            return candidates[0]

        for candidate in candidates:
            if self._normalize_model_name(candidate) in available_models:
                return candidate

        raise ValueError(
            "当前账号无法访问任何候选 Gemini 模型，请检查 GEMINI_MODEL 或账号权限。"
        )

    def _build_gemini_model_candidates(self) -> List[str]:
        candidates: List[str] = []
        if self.custom_gemini_model:
            candidates.append(self.custom_gemini_model.strip())

        candidates.extend(DEFAULT_GEMINI_MODEL_CANDIDATES)

        deduped: List[str] = []
        seen = set()
        for candidate in candidates:
            normalized = self._normalize_model_name(candidate)
            if normalized in seen:
                continue
            deduped.append(candidate)
            seen.add(normalized)

        return deduped

    @staticmethod
    def _normalize_model_name(name: str) -> str:
        if not name:
            return ""
        return name.split("/")[-1]

    def search_recent_ai_news(
        self,
        query: str = "AI artificial intelligence developments news",
        days: int = 7,
        num_results: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Search Google for recent AI news using Custom Search API.

        Args:
            query: Search query string
            days: Number of past days to restrict search to
            num_results: Maximum number of results to return (max 10)

        Returns:
            List of dictionaries containing title, snippet, and URL for each result
        """
        try:
            logger.info(f"Searching for AI news from the past {days} days...")

            # Restrict search to past N days
            date_restrict = f"d{days}"

            # Execute the search
            result = (
                self.search_service.cse()
                .list(
                    q=query,
                    cx=self.google_cse_id,
                    dateRestrict=date_restrict,
                    num=min(num_results, 10),  # Google Custom Search max is 10
                )
                .execute()
            )

            if "items" not in result:
                logger.warning("No search results found for the given criteria")
                return []

            # Format results
            formatted_results = []
            for item in result["items"]:
                formatted_results.append(
                    {
                        "title": item.get("title", "No title"),
                        "snippet": item.get("snippet", "No snippet"),
                        "url": item.get("link", "No URL"),
                    }
                )

            logger.info(f"Found {len(formatted_results)} search results")
            return formatted_results

        except HttpError as e:
            logger.error(f"Google Search API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return []

    def summarize_with_gemini(
        self, search_results: List[Dict[str, str]], report_type: str = "weekly"
    ) -> str:
        """
        Summarize search results using Gemini API.

        Args:
            search_results: List of search result dictionaries
            report_type: Type of report (weekly, monthly, etc.)

        Returns:
            Generated summary text
        """
        try:
            if not search_results:
                return "No search results available for summarization."

            logger.info(f"Summarizing {len(search_results)} articles with Gemini...")

            # Create comprehensive prompt
            prompt_lines = [
                "你是一位专业的AI行业分析师。请分析以下过去一周AI社区的最新发展动态。",
                "",
                "请提供一份简洁、高层次的总结，重点关注：",
                "1. 主要技术突破和创新",
                "2. 重要的公司动态和投资消息",
                "3. 开源项目和社区发展",
                "4. 政策法规和行业标准变化",
                "5. 新兴应用场景和商业化进展",
                "",
                "请将信息综合成一个连贯的概览，而不是简单地罗列文章。",
                "使用中文输出，保持专业性和可读性。",
                "",
                "--- 搜索结果 ---",
            ]

            # Add search results to prompt
            for i, item in enumerate(search_results, 1):
                prompt_lines.extend(
                    [
                        f"\n结果 {i}:",
                        f"标题: {item['title']}",
                        f"摘要: {item['snippet']}",
                        f"链接: {item['url']}",
                    ]
                )

            prompt_lines.extend(
                ["\n--- 分析总结 ---", "请基于以上信息提供你的专业分析总结："]
            )

            prompt = "\n".join(prompt_lines)

            # Generate summary
            response = self.gemini_model.generate_content(prompt)

            if not response.text:
                return "无法生成摘要，请检查API配置。"

            return response.text

        except Exception as e:
            logger.error(f"Gemini summarization error: {e}")
            return f"摘要生成失败: {str(e)}"

    def generate_weekly_report(
        self, custom_query: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Generate a complete weekly AI industry report.

        Args:
            custom_query: Optional custom search query

        Returns:
            Dictionary containing report data and metadata
        """
        try:
            # Default search queries for comprehensive coverage
            queries = [
                custom_query or "AI artificial intelligence developments news",
                "machine learning breakthroughs 2024",
                "generative AI news updates",
                "AI startup funding investment",
                "open source AI models release",
            ]

            all_results = []
            for query in queries:
                results = self.search_recent_ai_news(query, days=7, num_results=5)
                all_results.extend(results)

            # Remove duplicates based on URL
            seen_urls = set()
            unique_results = []
            for result in all_results:
                if result["url"] not in seen_urls:
                    seen_urls.add(result["url"])
                    unique_results.append(result)

            if not unique_results:
                return {
                    "success": False,
                    "error": "No search results found",
                    "report_date": datetime.now().isoformat(),
                    "summary": "本周未找到相关AI行业新闻。",
                }

            # Generate summary
            summary = self.summarize_with_gemini(unique_results)

            return {
                "success": True,
                "report_date": datetime.now().isoformat(),
                "articles_found": len(unique_results),
                "summary": summary,
                "sources": unique_results[:10],  # Include top 10 sources
            }

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_date": datetime.now().isoformat(),
                "summary": f"报告生成失败: {str(e)}",
            }


def main():
    """Main execution function."""
    print("🤖 AI行业周报生成器启动中...")
    print("=" * 50)

    try:
        # Initialize reporter
        reporter = AIIndustryReporter()

        # Generate report
        report = reporter.generate_weekly_report()

        if report["success"]:
            print(f"📅 报告日期: {report['report_date']}")
            print(f"📰 发现文章: {report['articles_found']} 篇")
            print("\n" + "=" * 50)
            print("🔥 AI行业周报总结 🔥")
            print("=" * 50)
            print(report["summary"])

            # Save report to file
            report_filename = (
                f"ai_weekly_report_{datetime.now().strftime('%Y%m%d')}.json"
            )
            with open(report_filename, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            print(f"\n📄 完整报告已保存至: {report_filename}")

        else:
            print(f"❌ 报告生成失败: {report.get('error', '未知错误')}")
            print(f"📝 错误详情: {report.get('summary', '无详细信息')}")
            sys.exit(1)

    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("\n请确保设置了以下环境变量:")
        print("- GOOGLE_CSE_API_KEY: Google Custom Search API密钥")
        print("- GOOGLE_CSE_ID: 自定义搜索引擎ID")
        print("- GEMINI_API_KEY: Gemini API密钥")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
