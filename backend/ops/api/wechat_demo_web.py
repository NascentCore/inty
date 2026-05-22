"""Serve minimal WeChat self-service demo page on Ops."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

_WECHAT_DEMO_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Inty WeChat Demo</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; }
    label { display: block; margin-top: 0.75rem; font-weight: 600; }
    input { width: 100%; box-sizing: border-box; margin-top: 0.25rem; padding: 0.4rem; }
    button { margin-top: 1rem; margin-right: 0.5rem; padding: 0.5rem 1rem; }
    #status { margin-top: 1rem; white-space: pre-wrap; background: #f4f4f4; padding: 0.75rem; }
    #qr img { max-width: 16rem; margin-top: 0.5rem; }
    #qr a { word-break: break-all; }
  </style>
</head>
<body>
  <h1>WeChat ↔ Inty Demo</h1>
  <p>Paste Inty credentials, scan WeChat QR, then DM the logged-in account.</p>
  <label>Inty API Base URL
    <input id="apiBase" type="text" value="http://127.0.0.1:8001" />
  </label>
  <label>Inty JWT (Bearer)
    <input id="jwt" type="password" autocomplete="off" />
  </label>
  <label>Agent ID
    <input id="agentId" type="text" />
  </label>
  <button id="startBtn" type="button">Start QR Login</button>
  <button id="stopBtn" type="button" disabled>Stop</button>
  <div id="qr"></div>
  <pre id="status">Idle.</pre>
  <script>
    const API = "/api/v1/wechat-demo";
    let sessionId = null;
    let pollTimer = null;

    function setStatus(text) {
      document.getElementById("status").textContent = text;
    }

    function renderQr(url) {
      const el = document.getElementById("qr");
      if (!url) { el.innerHTML = ""; return; }
      const imgUrl = "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data="
        + encodeURIComponent(url);
      el.innerHTML = '<p>Scan with WeChat:</p>'
        + '<img alt="QR" src="' + imgUrl + '" />'
        + '<p><a href="' + url + '" target="_blank" rel="noopener">' + url + '</a></p>';
    }

    async function pollSession() {
      if (!sessionId) return;
      const res = await fetch(API + "/sessions/" + sessionId);
      const body = await res.json();
      if (!res.ok) {
        setStatus("Poll error: " + JSON.stringify(body));
        return;
      }
      const s = body.data;
      const lines = [
        "session_id: " + s.session_id,
        "phase: " + s.phase,
        "qr_phase: " + (s.qr_phase || "-"),
        "bridge_running: " + s.bridge_running,
        "error: " + (s.error || "-"),
      ];
      setStatus(lines.join("\\n"));
      if (s.qrcode_url) renderQr(s.qrcode_url);
      if (s.phase === "bridge_running") {
        document.getElementById("startBtn").disabled = true;
        document.getElementById("stopBtn").disabled = false;
      }
      if (s.phase === "stopped" || s.phase === "failed") {
        clearInterval(pollTimer);
        pollTimer = null;
        document.getElementById("startBtn").disabled = false;
        document.getElementById("stopBtn").disabled = true;
      }
    }

    document.getElementById("startBtn").onclick = async () => {
      const payload = {
        inty_api_base_url: document.getElementById("apiBase").value.trim(),
        inty_jwt: document.getElementById("jwt").value.trim(),
        agent_id: document.getElementById("agentId").value.trim(),
      };
      setStatus("Starting session...");
      document.getElementById("qr").innerHTML = "";
      try {
        const res = await fetch(API + "/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const body = await res.json();
        if (!res.ok || !body.data) {
          setStatus("Start failed: " + JSON.stringify(body));
          return;
        }
        sessionId = body.data.session_id;
        document.getElementById("stopBtn").disabled = false;
        await pollSession();
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(pollSession, 2000);
      } catch (err) {
        setStatus("Start error: " + String(err));
      }
    };

    document.getElementById("stopBtn").onclick = async () => {
      if (!sessionId) return;
      await fetch(API + "/sessions/" + sessionId + "/stop", { method: "POST" });
      await pollSession();
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    };
  </script>
</body>
</html>
"""


def configure_wechat_demo_web_routes(app: FastAPI) -> None:
    """Mount ``GET /wechat-demo`` (internal demo; not in OpenAPI)."""

    @app.get("/wechat-demo", include_in_schema=False)
    async def wechat_demo_page() -> HTMLResponse:
        return HTMLResponse(_WECHAT_DEMO_HTML)
