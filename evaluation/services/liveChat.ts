/**
 * 实时语音通话 WebSocket 服务
 * CREATED_BY_AGENT
 */

import { getGlobalApiKey } from "./api";

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

export interface LiveChatCallbacks {
  onAudioReceived: (audioData: ArrayBuffer) => void;
  onTranscript: (text: string, role: "user" | "assistant") => void;
  onStatusChange: (status: ConnectionStatus, message?: string) => void;
  onError: (code: string, message: string) => void;
}

interface WebSocketMessage {
  type: string;
  data?: string;
  text?: string;
  status?: string;
  message?: string;
  code?: string;
  sample_rate?: number;
  is_final?: boolean;
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
    const wsUrl = `${protocol}//${host}/api/v1/live-chat/${config.agentId}?token=${apiKey}`;

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("WebSocket 连接已建立");
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
            message.code || "UNKNOWN",
            message.message || "未知错误",
          );
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
  }

  private queueAudio(audioData: ArrayBuffer): void {
    this.audioQueue.push(audioData);
    if (!this.isPlaying) {
      this.playNextAudio();
    }
  }

  private async playNextAudio(): Promise<void> {
    if (this.audioQueue.length === 0) {
      this.isPlaying = false;
      console.log("所有音频播放完成，恢复录音发送");
      return;
    }

    this.isPlaying = true;
    const audioData = this.audioQueue.shift()!;

    try {
      // 使用专门的播放 AudioContext（24kHz）
      if (!this.playbackContext || this.playbackContext.state === "closed") {
        this.playbackContext = new AudioContext();
        console.log(
          `创建播放 AudioContext，采样率: ${this.playbackContext.sampleRate}Hz`,
        );
      }

      const pcmData = new Int16Array(audioData);
      const floatData = new Float32Array(pcmData.length);

      for (let i = 0; i < pcmData.length; i++) {
        floatData[i] = pcmData[i] / 32768;
      }

      console.log(
        `播放音频: ${floatData.length} 样本, AudioContext 状态: ${this.playbackContext.state}`,
      );

      // 确保 AudioContext 在播放状态
      if (this.playbackContext.state === "suspended") {
        console.log("播放 AudioContext 被暂停，正在恢复...");
        await this.playbackContext.resume();
      }

      // 使用原始 24kHz 采样率创建 buffer
      const audioBuffer = this.playbackContext.createBuffer(
        1,
        floatData.length,
        RECEIVE_SAMPLE_RATE,
      );
      audioBuffer.getChannelData(0).set(floatData);

      const source = this.playbackContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.playbackContext.destination);

      source.onended = () => {
        console.log("音频片段播放完成，继续播放下一个");
        this.playNextAudio();
      };

      source.start();
      console.log(`音频开始播放，队列剩余: ${this.audioQueue.length}`);
    } catch (error) {
      console.error("播放音频失败:", error);
      this.playNextAudio();
    }
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
