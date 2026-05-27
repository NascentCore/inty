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
    .action-block { margin-top: 1rem; }
    .action-block > button { margin-top: 0; }
    .btn-hint { font-size: 0.85rem; color: #444; margin: 0.35rem 0 0; line-height: 1.45; max-width: 40rem; }
    #status { margin-top: 1rem; white-space: pre-wrap; background: #f4f4f4; padding: 0.75rem; }
    #qr img { max-width: 16rem; margin-top: 0.5rem; }
    #qr a { word-break: break-all; }
  </style>
</head>
<body>
  <h1>WeChat ↔ Inty Demo</h1>
  <p>Paste Inty credentials, scan WeChat QR, then DM the logged-in account.</p>
  <label>Inty JWT (Bearer)
    <input id="jwt" type="password" autocomplete="off" />
  </label>
  <label>Agent ID
    <input id="agentId" type="text" />
  </label>
  <div class="action-block">
    <button id="startBtn" type="button" title="New session: QR login then WeChat↔Inty bridge">Start QR Login</button>
    <p class="btn-hint" id="startHint">
      <strong>Start QR Login</strong> 创建新 <code>session_id</code>，走 iLink 扫码（QR 轮询最长约 8 分钟；
      单张 QR 过期会自动刷新）。扫码确认后进入 <code>bridge_running</code>：拉起微信 Hermes long-poll，
      并以表单中的 JWT / Agent ID 连接当前 Ops 同源上的 Inty <code>/api/v1/chat/ws</code>。
      bridge 凭证会写入 Postgres <code>ops_wechat_demo_bridges</code>；<em>仅重启 Ops</em> 时可无 QR 恢复
      （见下方 Stop 说明）。此前若点过 Stop，需重新 Start（可能要再扫码）。
      扫码后的 iLink <code>bot_token</code>（<code>weixin_token</code>）<strong>无协议公布的固定分钟/小时数</strong>，
      失效以 iLink 返回 <code>errcode=-14</code>（会话过期，不是「14 分钟」）为准，届时需重新扫码。
    </p>
  </div>
  <div class="action-block">
    <button id="stopBtn" type="button" disabled title="End bridge; DMs stop until Start QR Login again">Stop</button>
    <p class="btn-hint" id="stopHint">
      <strong>Stop</strong> 会结束当前 bridge：关闭微信侧 iLink/Hermes long-poll 与 Inty
      <code>/api/v1/chat/ws</code> 长连接，并删除 Postgres
      <code>ops_wechat_demo_bridges</code> 中该 session 的行（之后仅重启 Ops <em>不会</em> 自动恢复，无需再扫码的那条路径失效）。
      此后微信 DM 不会再收到 companion 回复，需重新点 <strong>Start QR Login</strong>（必要时再扫码）。
      这是主动拆桥，不是暂停；与只停 Ops 进程、靠 DB 行 restore 不同。
    </p>
  </div>
  <div id="qr"></div>
  <pre id="status">Idle.</pre>
  <script>
    const API = "/api/v1/wechat-demo";
    let sessionId = null;
    let pollTimer = null;
    let poll404Count = 0;
    const POLL_404_GIVE_UP = 15;

    function setStatus(text) {
      document.getElementById("status").textContent = text;
    }

    function renderQr(url) {
      const el = document.getElementById("qr");
      if (!url) { el.innerHTML = ""; return; }
      // TODO: replace qrserver.com with backend-generated PNG via Python qrcode package
      // (https://pypi.org/project/qrcode/) — e.g. GET /sessions/{id}/qrcode or inline base64.
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
        if (res.status === 404 && poll404Count < POLL_404_GIVE_UP) {
          poll404Count += 1;
          setStatus(
            "Session not in memory yet (poll " + poll404Count + "/" + POLL_404_GIVE_UP
            + "). Ops may be restoring bridge after restart."
          );
          return;
        }
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        if (res.status === 404) sessionId = null;
        renderQr("");
        document.getElementById("startBtn").disabled = false;
        document.getElementById("stopBtn").disabled = true;
        const msg = res.status === 404
          ? "Session not found. Click Start QR Login again."
          : "Poll error (" + res.status + "): " + JSON.stringify(body);
        setStatus(msg);
        return;
      }
      poll404Count = 0;
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
        inty_api_base_url: window.location.origin,
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
        poll404Count = 0;
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
