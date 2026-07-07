/**
 * 实时语音通话 WebSocket 服务
 * CREATED_BY_AGENT
 */

import { getGlobalApiKey, getAssumeUserId } from "./api";

export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "speaking"
  | "listening"
  | "disconnected"
  | "error";

export interface LiveChatConfig {
  agentId: string;
}

export interface SessionInfo {
  remainingDuration: number;
  agentLimit: number;
  agentCount: number;
}

export interface LatencyMetrics {
  connectLatencyMs?: number;
  firstResponseAfterSilenceMs?: number;
  turnLatenciesMs?: number[];
  avgTurnLatencyMs?: number;
}

export interface LiveChatCallbacks {
  onAudioReceived: (audioData: ArrayBuffer) => void;
  onTranscript: (text: string, role: "user" | "assistant") => void;
  onStatusChange: (status: ConnectionStatus, message?: string) => void;
  onError: (code: string, message: string) => void;
  onSessionInfo?: (info: SessionInfo) => void;
  onLatencyUpdate?: (metrics: LatencyMetrics) => void;
}

interface WebSocketMessage {
  type: string;
  data?: string;
  text?: string;
  status?: string;
  message?: string;
  code?: number | string;
  error_code?: string;
  sample_rate?: number;
  is_final?: boolean;
  remaining_duration?: number;
  agent_limit?: number;
  agent_count?: number;
  connect_latency_ms?: number;
  first_response_after_silence_ms?: number;
  turn_latencies_ms?: number[];
  avg_turn_latency_ms?: number;
}

const SEND_SAMPLE_RATE = 16000;
const RECEIVE_SAMPLE_RATE = 24000;
const BUFFER_SIZE = 4096;

export class LiveChatService {
  private ws: WebSocket | null = null;
  private recordingContext: AudioContext | null = null; // 录音用 AudioContext
  private playbackContext: AudioContext | null = null; // 播放用 AudioContext
  private mediaStream: MediaStream | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private callbacks: LiveChatCallbacks | null = null;
  private config: LiveChatConfig | null = null;
  private status: ConnectionStatus = "idle";
  private isRecording = false;
  private audioQueue: ArrayBuffer[] = [];
  private isPlaying = false;
  private isSpeaking = false; // AI 是否正在说话

  // 预调度播放相关 - 用于消除音频片段之间的间隙
  private nextPlayTime: number = 0; // 下一个片段的预定播放时间
  private isScheduling: boolean = false; // 是否正在调度播放
  private scheduleTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private readonly PREFILL_COUNT = 2; // 开始播放前预缓冲片段数
  private readonly SCHEDULE_AHEAD_MS = 50; // 提前调度时间（毫秒）

  // 保持向后兼容
  private get audioContext(): AudioContext | null {
    return this.recordingContext;
  }
  private set audioContext(value: AudioContext | null) {
    this.recordingContext = value;
  }

  async connect(
    config: LiveChatConfig,
    callbacks: LiveChatCallbacks,
  ): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      throw new Error("Already connected");
    }

    this.config = config;
    this.callbacks = callbacks;
    this.status = "connecting";
    callbacks.onStatusChange("connecting", "正在连接...");

    const apiKey = getGlobalApiKey();
    if (!apiKey) {
      throw new Error("API Key 未设置");
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    let wsUrl = `${protocol}//${host}/api/v1/live-chat/${config.agentId}?token=${apiKey}`;
    const assumeId = getAssumeUserId();
    if (assumeId && assumeId.trim()) {
      wsUrl += `&assume_user_id=${encodeURIComponent(assumeId.trim())}`;
    }

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("WebSocket 连接已建立");
        this.status = "connected";
        callbacks.onStatusChange("connected", "已连接");
        resolve();
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event.data);
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket 错误:", error);
        this.status = "error";
        callbacks.onError("WS_ERROR", "WebSocket 连接错误");
        reject(new Error("WebSocket connection failed"));
      };

      this.ws.onclose = (event) => {
        console.log("WebSocket 连接已关闭:", event.code, event.reason);

        // 解析服务端返回的错误信息（用量超限等场景）
        if (event.reason) {
          try {
            const errorInfo = JSON.parse(event.reason);
            if (errorInfo.type === "error" && errorInfo.error_code) {
              this.status = "error";
              callbacks.onError(
                errorInfo.error_code,
                errorInfo.message || "连接被拒绝",
              );
              callbacks.onStatusChange("error", errorInfo.message);
              this.cleanup();
              return;
            }
          } catch {
            // reason 不是 JSON 格式，继续正常处理
          }
        }

        this.status = "disconnected";
        callbacks.onStatusChange("disconnected", "连接已断开");
        this.cleanup();
      };
    });
  }

  private handleMessage(data: string): void {
    if (!this.callbacks) return;

    try {
      const message: WebSocketMessage = JSON.parse(data);

      switch (message.type) {
        case "audio_response":
          if (message.data) {
            console.log(
              `收到 AI 音频响应: ${message.data.length} 字符 (Base64)`,
            );
            const audioData = this.base64ToArrayBuffer(message.data);
            console.log(`解码后音频数据: ${audioData.byteLength} bytes`);
            this.queueAudio(audioData);
            this.callbacks.onAudioReceived(audioData);
          }
          break;

        case "transcript":
          if (message.text) {
            this.callbacks.onTranscript(message.text, "assistant");
          }
          break;

        case "user_transcript":
          if (message.text) {
            this.callbacks.onTranscript(message.text, "user");
          }
          break;

        case "status":
          if (message.status) {
            this.status = this.mapStatus(message.status);
            // 更新 AI 说话状态，用于避免回声
            this.isSpeaking = message.status === "speaking";
            console.log(
              `状态更新: ${message.status}, AI 说话中: ${this.isSpeaking}`,
            );
            this.callbacks.onStatusChange(this.status, message.message);
          }
          break;

        case "error":
          this.callbacks.onError(
            message.error_code || String(message.code) || "UNKNOWN",
            message.message || "未知错误",
          );
          // 收到错误消息后自动停止录音并断开连接
          this.stopRecording();
          this.status = "error";
          this.callbacks.onStatusChange("error", message.message);
          // 关闭 WebSocket 连接，确保 isConnected() 返回 false
          if (this.ws) {
            this.ws.close();
          }
          break;

        case "session_info":
          if (this.callbacks.onSessionInfo) {
            this.callbacks.onSessionInfo({
              remainingDuration: message.remaining_duration || 0,
              agentLimit: message.agent_limit || 0,
              agentCount: message.agent_count || 0,
            });
            console.log(
              `收到会话信息: 剩余时长 ${message.remaining_duration}s, ` +
                `agent 限制 ${message.agent_limit}, 已聊 ${message.agent_count}`,
            );
          }
          break;

        case "latency_update":
          if (this.callbacks.onLatencyUpdate) {
            const metrics: Record<string, number | number[] | undefined> = {};
            if (message.connect_latency_ms != null) {
              metrics.connectLatencyMs = message.connect_latency_ms;
            }
            if (message.first_response_after_silence_ms != null) {
              metrics.firstResponseAfterSilenceMs =
                message.first_response_after_silence_ms;
            }
            if (message.turn_latencies_ms != null) {
              metrics.turnLatenciesMs = message.turn_latencies_ms;
            }
            if (message.avg_turn_latency_ms != null) {
              metrics.avgTurnLatencyMs = message.avg_turn_latency_ms;
            }
            this.callbacks.onLatencyUpdate(metrics);
            console.log(`收到延迟指标更新:`, metrics);
          }
          break;

        default:
          console.warn("未知消息类型:", message.type);
      }
    } catch (error) {
      console.error("解析消息失败:", error);
    }
  }

  private mapStatus(status: string): ConnectionStatus {
    const statusMap: Record<string, ConnectionStatus> = {
      connecting: "connecting",
      connected: "connected",
      speaking: "speaking",
      listening: "listening",
      disconnected: "disconnected",
      error: "error",
    };
    return statusMap[status] || "idle";
  }

  async startRecording(): Promise<void> {
    if (this.isRecording) return;

    try {
      // 全双工模式：持续发送麦克风数据，需要启用回声消除来过滤 AI 播放的声音
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });

      // 使用浏览器原生采样率，然后手动重采样到 16kHz
      this.audioContext = new AudioContext();
      const nativeSampleRate = this.audioContext.sampleRate;
      console.log(
        `浏览器原生采样率: ${nativeSampleRate}Hz，目标采样率: ${SEND_SAMPLE_RATE}Hz`,
      );

      // 如果 AudioContext 被暂停，尝试恢复
      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }

      this.sourceNode = this.audioContext.createMediaStreamSource(
        this.mediaStream,
      );

      this.scriptProcessor = this.audioContext.createScriptProcessor(
        BUFFER_SIZE,
        1,
        1,
      );

      this.scriptProcessor.onaudioprocess = (event) => {
        if (!this.isRecording || !this.ws) return;

        // 全双工模式：持续发送麦克风数据
        // Gemini Live API 需要两条并行通道：发送和接收不能互相等待
        // 浏览器的回声消除会过滤掉 AI 播放的声音

        const inputData = event.inputBuffer.getChannelData(0);

        // 重采样到 16kHz
        const resampledData = this.resample(
          inputData,
          nativeSampleRate,
          SEND_SAMPLE_RATE,
        );
        const pcmData = this.floatTo16BitPCM(resampledData);
        const base64Data = this.arrayBufferToBase64(pcmData);

        this.sendAudio(base64Data);
      };

      this.sourceNode.connect(this.scriptProcessor);
      this.scriptProcessor.connect(this.audioContext.destination);

      this.isRecording = true;
      console.log("开始录音");
    } catch (error) {
      console.error("启动录音失败:", error);
      throw error;
    }
  }

  private resample(
    inputData: Float32Array,
    fromRate: number,
    toRate: number,
  ): Float32Array {
    if (fromRate === toRate) {
      return inputData;
    }

    const ratio = fromRate / toRate;
    const outputLength = Math.floor(inputData.length / ratio);
    const output = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * ratio;
      const srcIndexFloor = Math.floor(srcIndex);
      const srcIndexCeil = Math.min(srcIndexFloor + 1, inputData.length - 1);
      const t = srcIndex - srcIndexFloor;

      // 线性插值
      output[i] =
        inputData[srcIndexFloor] * (1 - t) + inputData[srcIndexCeil] * t;
    }

    return output;
  }

  stopRecording(): void {
    if (!this.isRecording) return;

    this.isRecording = false;

    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect();
      this.scriptProcessor = null;
    }

    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    console.log("停止录音");
  }

  private sendAudio(base64Data: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const message: WebSocketMessage = {
      type: "audio",
      data: base64Data,
    };
    this.ws.send(JSON.stringify(message));
  }

  sendText(text: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const message: WebSocketMessage = {
      type: "text",
      data: text,
    };
    this.ws.send(JSON.stringify(message));
  }

  disconnect(): void {
    this.stopRecording();

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = {
        type: "end",
      };
      this.ws.send(JSON.stringify(message));
      this.ws.close();
    }

    this.cleanup();
    this.status = "disconnected";
  }

  private cleanup(): void {
    this.stopRecording();

    // 清理调度定时器
    if (this.scheduleTimeoutId) {
      clearTimeout(this.scheduleTimeoutId);
      this.scheduleTimeoutId = null;
    }

    if (this.recordingContext) {
      this.recordingContext.close();
      this.recordingContext = null;
    }

    if (this.playbackContext) {
      this.playbackContext.close();
      this.playbackContext = null;
    }

    this.ws = null;
    this.audioQueue = [];
    this.isPlaying = false;
    // 重置预调度播放状态
    this.isScheduling = false;
    this.nextPlayTime = 0;
  }

  private queueAudio(audioData: ArrayBuffer): void {
    this.audioQueue.push(audioData);

    // 预缓冲机制：等待足够片段后再开始播放，避免启动时卡顿
    if (!this.isScheduling) {
      if (this.audioQueue.length >= this.PREFILL_COUNT) {
        this.startScheduledPlayback();
      }
    }
  }

  /**
   * 初始化并启动预调度播放
   */
  private async startScheduledPlayback(): Promise<void> {
    if (this.isScheduling) return;

    try {
      // 初始化播放 AudioContext，尝试使用 24kHz 采样率
      if (!this.playbackContext || this.playbackContext.state === "closed") {
        try {
          this.playbackContext = new AudioContext({
            sampleRate: RECEIVE_SAMPLE_RATE,
          });
          console.log(
            `创建播放 AudioContext，采样率: ${this.playbackContext.sampleRate}Hz (请求 ${RECEIVE_SAMPLE_RATE}Hz)`,
          );
        } catch {
          // 如果浏览器不支持指定采样率，回退到默认
          this.playbackContext = new AudioContext();
          console.log(
            `创建播放 AudioContext（回退），采样率: ${this.playbackContext.sampleRate}Hz`,
          );
        }
      }

      // 确保 AudioContext 在播放状态
      if (this.playbackContext.state === "suspended") {
        console.log("播放 AudioContext 被暂停，正在恢复...");
        await this.playbackContext.resume();
      }

      this.isScheduling = true;
      this.isPlaying = true;
      // 从当前时间开始调度
      this.nextPlayTime = this.playbackContext.currentTime;

      console.log(`开始预调度播放，队列中有 ${this.audioQueue.length} 个片段`);

      // 开始调度循环
      this.scheduleNextChunk();
    } catch (error) {
      console.error("启动预调度播放失败:", error);
      this.isScheduling = false;
      this.isPlaying = false;
    }
  }

  /**
   * 调度下一个音频片段播放
   * 使用精确时间调度实现无缝拼接
   */
  private scheduleNextChunk(): void {
    if (!this.playbackContext || this.playbackContext.state === "closed") {
      this.isScheduling = false;
      this.isPlaying = false;
      return;
    }

    if (this.audioQueue.length === 0) {
      // 队列为空，停止调度但保持 isPlaying 状态，等待新数据
      // 使用短暂延迟重新检查队列
      this.scheduleTimeoutId = setTimeout(() => {
        if (this.audioQueue.length > 0) {
          this.scheduleNextChunk();
        } else {
          // 超过一定时间没有新数据，结束播放
          console.log("音频队列持续为空，停止调度播放");
          this.isScheduling = false;
          this.isPlaying = false;
        }
      }, 200);
      return;
    }

    const audioData = this.audioQueue.shift()!;

    try {
      const audioBuffer = this.createAudioBuffer(audioData);

      const source = this.playbackContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.playbackContext.destination);

      // 关键：使用精确时间调度，确保无缝衔接
      const currentTime = this.playbackContext.currentTime;
      const startTime = Math.max(currentTime, this.nextPlayTime);

      source.start(startTime);

      // 计算下一片段的播放时间
      this.nextPlayTime = startTime + audioBuffer.duration;

      console.log(
        `调度播放: startTime=${startTime.toFixed(3)}s, duration=${audioBuffer.duration.toFixed(3)}s, 队列剩余: ${this.audioQueue.length}`,
      );

      // 提前调度下一个片段，确保无缝衔接
      const delayMs = Math.max(
        0,
        audioBuffer.duration * 1000 - this.SCHEDULE_AHEAD_MS,
      );
      this.scheduleTimeoutId = setTimeout(
        () => this.scheduleNextChunk(),
        delayMs,
      );
    } catch (error) {
      console.error("调度音频片段失败:", error);
      // 出错时继续尝试下一个片段
      this.scheduleTimeoutId = setTimeout(() => this.scheduleNextChunk(), 10);
    }
  }

  /**
   * 将 PCM 数据转换为 AudioBuffer
   */
  private createAudioBuffer(audioData: ArrayBuffer): AudioBuffer {
    if (!this.playbackContext) {
      throw new Error("PlaybackContext not initialized");
    }

    const pcmData = new Int16Array(audioData);
    const floatData = new Float32Array(pcmData.length);

    for (let i = 0; i < pcmData.length; i++) {
      floatData[i] = pcmData[i] / 32768;
    }

    const audioBuffer = this.playbackContext.createBuffer(
      1,
      floatData.length,
      RECEIVE_SAMPLE_RATE,
    );
    audioBuffer.getChannelData(0).set(floatData);

    return audioBuffer;
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  private floatTo16BitPCM(float32Array: Float32Array): ArrayBuffer {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);

    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }

    return buffer;
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }
}

export const liveChatService = new LiveChatService();
