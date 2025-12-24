// Plain JS client for Gemini native-audio websocket demo
// CREATED_BY_AGENT

const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");
const modeSelect = document.getElementById("mode");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");

const SERVER_ENDPOINT =
  "http://127.0.0.1:7242/ingest/6a49d023-12a7-4c9d-a405-893d236726d6";

function log(line) {
  const ts = new Date().toISOString();
  logEl.textContent += `[${ts}] ${line}\n`;
  logEl.scrollTop = logEl.scrollHeight;
}

// #region agent log
function debugLog(location, message, data) {
  fetch(SERVER_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      location,
      message,
      data,
      timestamp: Date.now(),
      sessionId: "debug-session",
      runId: "demo-web",
      hypothesisId: "DEMO_WEB",
    }),
  }).catch(() => {});
}
// #endregion

let ws = null;
let micStream = null;
let audioCtx = null;
let processor = null;

// playback
let playCtx = null;
let playTime = 0;

function setStatus(text) {
  statusEl.textContent = text;
}

function pcm16ToFloat32(int16) {
  const f32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    f32[i] = Math.max(-1, Math.min(1, int16[i] / 32768));
  }
  return f32;
}

function float32ToPCM16(float32) {
  const buf = new ArrayBuffer(float32.length * 2);
  const view = new DataView(buf);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Uint8Array(buf);
}

function resampleFloat32(input, inRate, outRate) {
  if (inRate === outRate) return input;
  const ratio = inRate / outRate;
  const outLen = Math.floor(input.length / ratio);
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const pos = i * ratio;
    const idx = Math.floor(pos);
    const frac = pos - idx;
    const a = input[idx] ?? 0;
    const b = input[idx + 1] ?? a;
    out[i] = a + (b - a) * frac;
  }
  return out;
}

function base64FromBytes(bytes) {
  let bin = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(bin);
}

function bytesFromBase64(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

async function ensurePlayCtx() {
  if (!playCtx || playCtx.state === "closed") {
    playCtx = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 24000,
    });
    playTime = playCtx.currentTime + 0.05;
  }
  if (playCtx.state === "suspended") await playCtx.resume();
}

async function playPcm24k(pcmBytes) {
  await ensurePlayCtx();
  const int16 = new Int16Array(
    pcmBytes.buffer,
    pcmBytes.byteOffset,
    pcmBytes.byteLength / 2
  );
  const f32 = pcm16ToFloat32(int16);
  const buffer = playCtx.createBuffer(1, f32.length, 24000);
  buffer.copyToChannel(f32, 0, 0);
  const src = playCtx.createBufferSource();
  src.buffer = buffer;
  src.connect(playCtx.destination);
  const startAt = Math.max(playTime, playCtx.currentTime + 0.01);
  src.start(startAt);
  playTime = startAt + buffer.duration;
}

async function start() {
  const mode = modeSelect.value;
  // 根据社区反馈（见 discuss 帖），single 模式可调低 silence_ms 以改善 VAD 行为
  const silenceMs = mode === "single" ? 300 : 500;
  const url = `ws://${location.host}/ws?mode=${encodeURIComponent(
    mode
  )}&silence_ms=${encodeURIComponent(String(silenceMs))}`;
  ws = new WebSocket(url);
  ws.onopen = () => {
    setStatus(`已连接（mode=${mode}）`);
    log(`WS open: ${url}`);
    debugLog("demo_web.js:ws_open", "ws_open", { mode, silenceMs });
  };
  ws.onclose = () => {
    setStatus("已断开");
    log("WS closed");
    debugLog("demo_web.js:ws_close", "ws_close", {});
  };
  ws.onerror = (e) => {
    log(`WS error: ${e?.message ?? "unknown"}`);
    debugLog("demo_web.js:ws_error", "ws_error", {});
  };
  ws.onmessage = async (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "status") {
      log(`status: ${msg.status}`);
      debugLog("demo_web.js:status", "status", { status: msg.status });
      return;
    }
    if (msg.type === "audio") {
      const bytes = bytesFromBase64(msg.data);
      // mime_type 通常是 audio/pcm;rate=24000
      await playPcm24k(bytes);
      return;
    }
    if (msg.type === "error") {
      log(`error: ${msg.message}`);
      return;
    }
  };

  micStream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const src = audioCtx.createMediaStreamSource(micStream);
  // ScriptProcessorNode 兼容性最好（demo）
  processor = audioCtx.createScriptProcessor(4096, 1, 1);
  src.connect(processor);
  processor.connect(audioCtx.destination);

  let packet = 0;
  processor.onaudioprocess = (e) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const input = e.inputBuffer.getChannelData(0);
    const resampled = resampleFloat32(input, audioCtx.sampleRate, 16000);
    const pcm = float32ToPCM16(resampled);
    const b64 = base64FromBytes(pcm);
    ws.send(JSON.stringify({ type: "audio", data: b64 }));

    packet += 1;
    if (packet <= 3 || packet % 200 === 0) {
      debugLog("demo_web.js:send_audio", "send_audio", {
        packet,
        bytes: pcm.byteLength,
        inRate: audioCtx.sampleRate,
      });
    }
  };
}

async function stop() {
  try {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "end" }));
      ws.close();
    }
  } catch {}
  ws = null;

  if (processor) {
    processor.disconnect();
    processor.onaudioprocess = null;
  }
  processor = null;

  if (audioCtx) {
    try {
      await audioCtx.close();
    } catch {}
  }
  audioCtx = null;

  if (micStream) {
    for (const t of micStream.getTracks()) t.stop();
  }
  micStream = null;

  setStatus("已停止");
  log("Stopped");
}

btnStart.onclick = async () => {
  btnStart.disabled = true;
  btnStop.disabled = false;
  logEl.textContent = "";
  try {
    await start();
  } catch (e) {
    log(`start failed: ${e?.message ?? String(e)}`);
    await stop();
    btnStart.disabled = false;
    btnStop.disabled = true;
  }
};

btnStop.onclick = async () => {
  btnStop.disabled = true;
  btnStart.disabled = false;
  await stop();
};

