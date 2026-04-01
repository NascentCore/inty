#!/usr/bin/env python3
"""
使用 GA4 Data API 查询 Firebase 事件参数的演示脚本。

示例：
    python experimental/firebase_events_params/fetch_button_clicked_params.py \
        --property-id 123456789 \
        --event-name button_clicked \
        --limit 20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

from app.core.config import global_config_loaded_from_config_yaml as global_config
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account
from tabulate import tabulate

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def resolve_service_account_path() -> Path:
    """根据通用配置解析 Firebase 服务账号 JSON 的绝对路径。"""
    service_account_path = Path(global_config.firebase.service_account_path)
    if service_account_path.is_absolute():
        return service_account_path
    return (REPO_ROOT / service_account_path).resolve()


def build_credentials():
    key_path = resolve_service_account_path()
    if not key_path.exists():
        raise FileNotFoundError(
            f"未找到服务账号文件：{key_path}\n"
            "请确认 config.yaml 中的 firebase.service_account_path 配置正确。"
        )

    scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
    return service_account.Credentials.from_service_account_file(
        str(key_path), scopes=scopes
    )


def fetch_event_parameters(
    property_id: str,
    event_name: str,
    start_date: str,
    end_date: str,
    limit: int = 20,
) -> List[Tuple[str, str, str, str]]:
    credentials = build_credentials()
    client = BetaAnalyticsDataClient(credentials=credentials)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[
            Dimension(name="eventName"),
            Dimension(name="eventParameterName"),
            Dimension(name="eventParameterValue"),
        ],
        metrics=[Metric(name="eventCount")],
        limit=limit,
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(value=event_name),
            )
        ),
    )

    response = client.run_report(request)
    rows: List[Tuple[str, str, str, str]] = []
    for row in response.rows:
        values = [value.value for value in row.dimension_values]
        metric_values = [value.value for value in row.metric_values]
        event_name_value = values[0] if len(values) > 0 else ""
        param_name = values[1] if len(values) > 1 else ""
        param_value = values[2] if len(values) > 2 else ""
        event_count = metric_values[0] if metric_values else "0"
        rows.append((event_name_value, param_name, param_value, event_count))

    return rows


def print_rows(rows: Sequence[Tuple[str, str, str, str]]) -> None:
    if not rows:
        print("没有查询到事件参数记录。")
        return

    headers = ["事件名", "参数名", "参数值", "事件计数"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="查询 Firebase GA4 事件的参数分布。")
    parser.add_argument(
        "--property-id",
        required=True,
        help="GA4 Property ID（仅数字）。",
    )
    parser.add_argument(
        "--event-name",
        default="button_clicked",
        help="需要查询的事件名称，默认为 button_clicked。",
    )
    parser.add_argument(
        "--start-date",
        default="7daysAgo",
        help="查询起始日期，支持相对日期（如 7daysAgo）或 YYYY-MM-DD。",
    )
    parser.add_argument(
        "--end-date",
        default="today",
        help="查询结束日期，支持相对日期（如 today）或 YYYY-MM-DD。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="返回的最大记录数，默认为 20。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅输出解析后的服务账号路径，不执行 API 请求。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    account_path = resolve_service_account_path()

    if args.dry_run:
        print(f"[Dry-Run] 服务账号路径：{account_path}")
        return

    rows = fetch_event_parameters(
        property_id=args.property_id,
        event_name=args.event_name,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit,
    )
    print(
        "查询成功：property={property}, event={event}, start={start}, end={end}, returned={count}".format(
            property=args.property_id,
            event=args.event_name,
            start=args.start_date,
            end=args.end_date,
            count=len(rows),
        )
    )
    print_rows(rows)


if __name__ == "__main__":
    main()
