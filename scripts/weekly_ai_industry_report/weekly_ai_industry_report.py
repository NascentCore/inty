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
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

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

DEFAULT_GEMINI_MODEL = "gemini-flash-latest"


class AIIndustryReporter:
    """Main class for generating AI industry weekly reports."""

    def __init__(self):
        """Initialize the reporter with API keys from environment variables."""
        self.google_api_key = os.getenv("GOOGLE_CSE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

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
        logger.info(f"Using Gemini model: {DEFAULT_GEMINI_MODEL}")
        self.gemini_model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)

        # Build Google Custom Search service
        self.search_service = build(
            "customsearch", "v1", developerKey=self.google_api_key
        )

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
    ) -> Dict[str, Any]:
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


@dataclass
class FeishuNotificationResult:
    status: str  # success, skipped, failed
    detail: str = ""


class FeishuNotifier:
    """Send formatted weekly report messages to a Feishu group bot."""

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        if not webhook_url:
            raise ValueError("Webhook URL is required for Feishu notifications")

        self.webhook_url = webhook_url
        self.secret = secret

    def send_report(self, report: Dict[str, Any]) -> None:
        payload = self._build_payload(report)
        self._post(payload)

    def _build_payload(self, report: Dict[str, Any]) -> Dict[str, Any]:
        report_date = report.get("report_date", "")[:10] or datetime.now().strftime(
            "%Y-%m-%d"
        )
        summary = (report.get("summary") or "").strip()
        if not summary:
            summary = "（本周暂无可用摘要）"

        summary = self._truncate(summary, 1000)

        sources_md = self._build_sources_md(report.get("sources", []))

        elements: List[Dict[str, Any]] = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**📝 摘要**\n{summary}",
                },
            }
        ]

        if sources_md:
            elements.extend(
                [
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": sources_md},
                    },
                ]
            )

        elements.append(
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "自动推送 · 如需修改请联系 Inty 团队",
                    }
                ],
            }
        )

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": f"AI行业周报 · {report_date}"},
            },
            "elements": elements,
        }

        payload: Dict[str, Any] = {
            "msg_type": "interactive",
            "card": card,
        }

        if self.secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = self._generate_signature(timestamp)

        return payload

    def _build_sources_md(self, sources: List[Dict[str, str]]) -> str:
        if not sources:
            return ""

        lines = ["**🔗 重点来源（前5条）**"]
        for item in sources[:5]:
            title = (item.get("title") or "未命名来源").strip()
            url = item.get("url", "").strip()
            if url:
                lines.append(f"- [{title}]({url})")
            else:
                lines.append(f"- {title}")

        return "\n".join(lines)

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "…"

    def _generate_signature(self, timestamp: str) -> str:
        """Compute Feishu bot signature when a secret is configured."""
        if not self.secret:
            return ""

        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    def _post(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_obj = urllib_request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(request_obj, timeout=10) as response:
                response_body = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
            raise RuntimeError(
                f"飞书Webhook请求失败，HTTP {exc.code}, body: {error_body}"
            ) from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"无法连接飞书Webhook: {exc.reason}") from exc

        if not response_body:
            return

        try:
            response_json = json.loads(response_body)
        except json.JSONDecodeError:
            logger.warning("飞书Webhook返回非JSON: %s", response_body)
            return

        status_code = response_json.get("StatusCode")
        if status_code is None:
            status_code = response_json.get("code")

        if status_code not in (None, 0):
            raise RuntimeError(f"飞书Webhook返回错误: {response_json}")


def send_report_to_feishu(report: Dict[str, Any]) -> FeishuNotificationResult:
    """Send the generated report to Feishu if webhook env vars are configured."""

    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        return FeishuNotificationResult(
            status="skipped", detail="环境变量 FEISHU_WEBHOOK_URL 未配置，跳过推送"
        )

    secret = os.getenv("FEISHU_WEBHOOK_SECRET")
    notifier = FeishuNotifier(webhook_url=webhook_url, secret=secret)

    try:
        notifier.send_report(report)
        return FeishuNotificationResult(status="success")
    except Exception as exc:
        logger.error(f"Feishu notification failed: {exc}")
        return FeishuNotificationResult(status="failed", detail=str(exc))


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

            feishu_result = send_report_to_feishu(report)
            if feishu_result.status == "success":
                print("✅ 已推送至飞书群机器人")
            elif feishu_result.status == "failed":
                print(f"⚠️ 飞书推送失败: {feishu_result.detail}")
            else:
                print("ℹ️ 未配置飞书Webhook，已跳过飞书推送")

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
