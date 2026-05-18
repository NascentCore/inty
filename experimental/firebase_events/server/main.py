"""CREATED_BY_AGENT"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

DATA_PATH = Path(__file__).parent / "sample_data" / "events.json"
DIMENSION_EXTRACTORS = {
    "geo_country": lambda row: row.get("geo", {}).get("country", "unknown"),
    "device_category": lambda row: row.get("device", {}).get(
        "category", "unknown"
    ),
    "app_version": lambda row: row.get("app", {}).get("version", "0.0"),
    "screen_class": lambda row: row.get("screen_class", "unknown"),
}

app = FastAPI(title="Firebase Analytics Demo Dashboard")


def _load_events() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return payload.get("events", [])


def _dimension_breakdown(
    rows: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {}
    for name, extractor in DIMENSION_EXTRACTORS.items():
        counter: Counter[str] = Counter()
        for row in rows:
            counter[str(extractor(row))] += 1
        result[name] = [
            {"value": value, "count": count}
            for value, count in counter.most_common(3)
        ]
    return result


def _summarize_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event.get("event_name", "(unknown)")].append(event)

    summaries: List[Dict[str, Any]] = []
    for event_name, rows in grouped.items():
        unique_users = {row.get("user_pseudo_id") for row in rows}
        values = [
            float(row.get("event_params", {}).get("value"))
            for row in rows
            if row.get("event_params", {}).get("value") is not None
        ]
        latest_params = rows[-1].get("event_params", {}) if rows else {}
        summaries.append(
            {
                "event_name": event_name,
                "count": len(rows),
                "unique_users": len(unique_users),
                "avg_value": (
                    round(sum(values) / len(values), 2) if values else None
                ),
                "dimension_breakdown": _dimension_breakdown(rows),
                "latest_params": latest_params,
            }
        )
    summaries.sort(key=lambda item: item["event_name"])
    return summaries


@app.get("/api/summary")
def summary() -> Dict[str, Any]:
    events = _load_events()
    return {
        "rows": _summarize_events(events),
        "total_events": len(events),
    }


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return """
    <!DOCTYPE html>
    <html lang=\"zh\">
    <head>
        <meta charset=\"utf-8\" />
        <title>Firebase Analytics Demo Dashboard</title>
        <style>
            body { font-family: system-ui, sans-serif; margin: 32px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 24px; }
            th, td { border: 1px solid #ddd; padding: 8px; }
            th { background: #f2f2f2; }
            code { background: #f9f9f9; padding: 2px 4px; }
        </style>
    </head>
    <body>
        <h1>Firebase Analytics Demo Dashboard</h1>
        <p>以下数据来自 sample_data/events.json，可替换为真实 BigQuery 导出。</p>
        <section id=\"summary\">加载中...</section>
        <script>
            async function render() {
                const res = await fetch('/api/summary');
                const payload = await res.json();
                const rows = payload.rows;
                if (!rows.length) {
                    document.getElementById('summary').innerText = '暂无数据';
                    return;
                }
                const tableRows = rows.map(row => `
                    <tr>
                        <td>${row.event_name}</td>
                        <td>${row.count}</td>
                        <td>${row.unique_users}</td>
                        <td>${row.avg_value ?? '-'}</td>
                        <td><pre>${JSON.stringify(row.dimension_breakdown, null, 2)}</pre></td>
                        <td><pre>${JSON.stringify(row.latest_params, null, 2)}</pre></td>
                    </tr>
                `).join('');
                document.getElementById('summary').innerHTML = `
                    <p>共 ${payload.total_events} 条事件。</p>
                    <table>
                        <thead>
                            <tr>
                                <th>事件名</th>
                                <th>事件数</th>
                                <th>去重用户</th>
                                <th>平均价值</th>
                                <th>维度 Top3</th>
                                <th>最近参数</th>
                            </tr>
                        </thead>
                        <tbody>${tableRows}</tbody>
                    </table>
                `;
            }
            render();
        </script>
    </body>
    </html>
    """
