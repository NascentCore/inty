"""Serve Telegram demo onboard page on Ops (agent_id → QR deep link)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

_TELEGRAM_DEMO_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Inty Telegram Demo</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; }
    label { display: block; margin-top: 1rem; font-weight: 600; }
    input { width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; }
    button { margin-top: 1rem; padding: 0.5rem 1rem; }
    .hint { font-size: 0.85rem; color: #444; margin: 0.75rem 0 0; line-height: 1.45; }
    #status { margin-top: 1rem; white-space: pre-wrap; background: #f4f4f4; padding: 0.75rem; }
    #qr img { max-width: 16rem; margin-top: 0.5rem; }
    #bot-info { margin-top: 0.5rem; }
  </style>
</head>
<body>
  <h1>Telegram ↔ Inty Demo</h1>
  <p class="hint">
    在 BotFather 创建的 bot token 写入 config ``agent.channels.telegram.bot_token`` 后，
    输入已有 companion 的 <code>agent_id</code>，扫码或点击链接在 Telegram 里开始聊天。
  </p>
  <div id="bot-info"></div>
  <label for="agent_id">agent_id</label>
  <input id="agent_id" type="text" placeholder="从 REPL 或数据库复制 agent UUID" />
  <button type="button" id="generate">生成 QR / 链接</button>
  <div id="qr"></div>
  <pre id="status">正在加载 bot 信息…</pre>
  <script>
    const API = "/api/v1/telegram-demo";

    function setStatus(text) {
      document.getElementById("status").textContent = text;
    }

    function renderQr(url) {
      const el = document.getElementById("qr");
      if (!url) { el.innerHTML = ""; return; }
      const imgUrl = "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data="
        + encodeURIComponent(url);
      el.innerHTML = '<p>请用 Telegram 扫码（或点下方链接）：</p>'
        + '<p><a href="' + url + '" target="_blank" rel="noopener">' + url + '</a></p>'
        + '<img alt="QR" src="' + imgUrl + '" />';
    }

    function deepLink(username, agentId) {
      const start = "agent_" + agentId.trim();
      return "https://t.me/" + username + "?start=" + encodeURIComponent(start);
    }

    async function loadBotInfo() {
      try {
        const res = await fetch(API + "/bot-info");
        const body = await res.json();
        if (!res.ok || !body.data) {
          setStatus("无法读取 bot 信息 (" + res.status + "): "
            + (body.detail || body.message || JSON.stringify(body)));
          return null;
        }
        const info = body.data;
        document.getElementById("bot-info").innerHTML =
          "<p>Bot: <code>@" + info.bot_username + "</code> (id " + info.bot_id + ")</p>";
        setStatus("填写 agent_id 后点击「生成 QR / 链接」。");
        return info;
      } catch (err) {
        setStatus("请求失败: " + String(err));
        return null;
      }
    }

    document.addEventListener("DOMContentLoaded", async () => {
      const botInfo = await loadBotInfo();
      document.getElementById("generate").addEventListener("click", () => {
        if (!botInfo) {
          setStatus("bot 信息未加载，请刷新页面。");
          return;
        }
        const agentId = document.getElementById("agent_id").value.trim();
        if (!agentId) {
          setStatus("请先输入 agent_id。");
          return;
        }
        const url = deepLink(botInfo.bot_username, agentId);
        renderQr(url);
        setStatus("扫码后在 Telegram 中发送中文消息测试。");
      });
    });
  </script>
</body>
</html>
"""


def configure_telegram_demo_web_routes(app: FastAPI) -> None:
    """Mount ``GET /telegram-demo`` (onboard demo; not in OpenAPI)."""

    @app.get("/telegram-demo", include_in_schema=False)
    async def telegram_demo_onboard_page() -> HTMLResponse:
        return HTMLResponse(_TELEGRAM_DEMO_HTML)
