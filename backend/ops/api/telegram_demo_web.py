"""Serve Telegram demo onboard page (team QR → auto provision)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

_TELEGRAM_DEMO_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Inty Telegram Demo</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
    .hint { font-size: 0.9rem; color: #444; margin: 0.75rem 0; }
    #status { margin-top: 1rem; white-space: pre-wrap; background: #f4f4f4; padding: 0.75rem; }
    #qr img { max-width: 16rem; margin-top: 0.5rem; }
    ol { padding-left: 1.25rem; }
  </style>
</head>
<body>
  <h1>Telegram ↔ Inty Demo</h1>
  <p class="hint">
    每人扫码后会自动创建独立的 companion（guest user + agent）。
  </p>
  <div id="bot-info"></div>
  <div id="qr"></div>
  <pre id="status">正在加载 bot 信息…</pre>
  <h2>队友使用指南</h2>
  <ol>
    <li>用 Telegram 扫上方 QR，或打开链接（会自动发送 <code>/start onboard</code>）</li>
    <li>在 bot 里用<strong>中文</strong>聊天，完成 bootstrap（取名、关系等）</li>
    <li>bootstrap 结束后正常闲聊；空闲时可能收到 proactive 消息</li>
    <li><strong>一人一个 companion</strong>；仅支持文字；勿与 App WebSocket 同时用同一 guest 账号</li>
    <li>Ops 重启后一般<strong>直接发消息</strong>即可；异常时再扫 QR 或发 <code>/start onboard</code></li>
    <li>无回复：确认 Ops <code>/health</code>、查看 <code>.inty/inty.log</code></li>
  </ol>
  <script>
    const API = "/api/v1/telegram-demo";

    function setStatus(text) {
      document.getElementById("status").textContent = text;
    }

    function renderQr(username) {
      const url = "https://t.me/" + username + "?start=onboard";
      const imgUrl = "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data="
        + encodeURIComponent(url);
      document.getElementById("qr").innerHTML =
        '<p>团队 QR / 链接：</p>'
        + '<p><a href="' + url + '" target="_blank" rel="noopener">' + url + '</a></p>'
        + '<img alt="QR" src="' + imgUrl + '" />';
    }

    async function loadBotInfo() {
      try {
        const res = await fetch(API + "/bot-info");
        const body = await res.json();
        if (!res.ok || !body.data) {
          setStatus("无法读取 bot 信息 (" + res.status + "): "
            + (body.detail || body.message || JSON.stringify(body)));
          return;
        }
        const info = body.data;
        document.getElementById("bot-info").innerHTML =
          "<p>Bot: <code>@" + info.bot_username + "</code> (id " + info.bot_id + ")</p>";
        renderQr(info.bot_username);
        setStatus("请用 Telegram 扫码开始；每人会获得独立 companion。");
      } catch (err) {
        setStatus("请求失败: " + String(err));
      }
    }

    document.addEventListener("DOMContentLoaded", loadBotInfo);
  </script>
</body>
</html>
"""


def configure_telegram_demo_web_routes(app: FastAPI) -> None:
    """Mount ``GET /telegram`` (onboard page; not in OpenAPI)."""

    @app.get("/telegram", include_in_schema=False)
    async def telegram_demo_onboard_page() -> HTMLResponse:
        return HTMLResponse(_TELEGRAM_DEMO_HTML)
