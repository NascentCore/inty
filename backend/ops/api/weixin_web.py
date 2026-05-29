"""Serve Weixin onboard page on Ops (QR login → auto user + agent provision)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

_WEIXIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Inty Weixin Onboard</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; }
    .hint { font-size: 0.85rem; color: #444; margin: 0.75rem 0 0; line-height: 1.45; max-width: 40rem; }
    #status { margin-top: 1rem; white-space: pre-wrap; background: #f4f4f4; padding: 0.75rem; }
    #qr img { max-width: 16rem; margin-top: 0.5rem; }
  </style>
</head>
<body>
  <h1>Weixin ↔ Inty Onboard</h1>
  <p>Scan WeChat QR to register or sign in; a companion agent is created after confirm.</p>
  <p class="hint">
    扫码后，如果微信提示二维码过期，请刷新页面重新生成二维码。
  </p>
  <div id="qr"></div>
  <pre id="status">正在获取二维码…</pre>
  <script>
    const API = "/api/v1/weixin";

    function setStatus(text) {
      document.getElementById("status").textContent = text;
    }

    function renderQr(url) {
      const el = document.getElementById("qr");
      if (!url) { el.innerHTML = ""; return; }
      const imgUrl = "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data="
        + encodeURIComponent(url);
      el.innerHTML = '<p>请使用微信扫码：</p>'
        + '<img alt="QR" src="' + imgUrl + '" />';
    }

    async function beginSession() {
      setStatus("正在获取二维码…");
      document.getElementById("qr").innerHTML = "";
      try {
        const res = await fetch(API + "/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ inty_api_base_url: window.location.origin }),
        });
        const body = await res.json();
        if (!res.ok || !body.data) {
          const msg = body.detail || body.message || JSON.stringify(body);
          setStatus(res.status === 504
            ? "获取二维码超时，请刷新页面重试。"
            : "无法开始会话 (" + res.status + "): " + msg);
          return;
        }
        const s = body.data;
        if (s.qrcode_url) renderQr(s.qrcode_url);
        setStatus("扫码成功后请在微信中与 Inty 对话。");
      } catch (err) {
        setStatus("请求失败: " + String(err));
      }
    }

    document.addEventListener("DOMContentLoaded", beginSession);
  </script>
</body>
</html>
"""


def configure_weixin_web_routes(app: FastAPI) -> None:
    """Mount ``GET /weixin`` (onboard demo; not in OpenAPI)."""

    @app.get("/weixin", include_in_schema=False)
    async def weixin_onboard_page() -> HTMLResponse:
        return HTMLResponse(_WEIXIN_HTML)
