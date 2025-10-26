import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Card, Input, Button, List, Typography, Space, Tag, message, Tooltip } from "antd";
import { SendOutlined, BgColorsOutlined, KeyOutlined } from "@ant-design/icons";
import type { Emotion } from "../services/gemini";
import { generateReplyWithEmotion, EMOTIONS } from "../services/gemini";
import { getEmotionBackgroundUrl } from "../services/emotionBackgrounds";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  emotion?: Emotion;
}

const GEMINI_KEY_STORAGE = "gemini_api_key";

export const Live2DEmotionChatDemo: React.FC = () => {
  const [apiKey, setApiKey] = useState<string>("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem(GEMINI_KEY_STORAGE) || "";
    setApiKey(saved);
  }, []);

  const backgroundEmotion: Emotion = useMemo(() => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.emotion);
    return (lastAssistant?.emotion as Emotion) || "Neutral";
  }, [messages]);

  const bgUrl = useMemo(() => getEmotionBackgroundUrl(backgroundEmotion), [backgroundEmotion]);

  const saveApiKey = useCallback(() => {
    const k = apiKey.trim();
    if (!k) {
      message.error("请输入 Gemini API Key");
      return;
    }
    localStorage.setItem(GEMINI_KEY_STORAGE, k);
    message.success("Gemini API Key 已保存");
  }, [apiKey]);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    const key = (localStorage.getItem(GEMINI_KEY_STORAGE) || apiKey).trim();
    if (!key) {
      message.error("请先设置 Gemini API Key");
      return;
    }

    const userMsg: ChatMessage = {
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);

    try {
      const result = await generateReplyWithEmotion(key, history, trimmed);
      const aiMsg: ChatMessage = {
        role: "assistant",
        content: result.reply,
        timestamp: new Date().toISOString(),
        emotion: result.emotion,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (e: any) {
      console.error(e);
      message.error(e?.message || "调用 Gemini 失败");
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }, [apiKey, input, messages, sending]);

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div style={{ height: "100%", padding: 24 }}>
      <Card
        title={
          <Space>
            <BgColorsOutlined />
            <Text strong>Live2D 情绪背景聊天（Gemini Demo）</Text>
            <Tag color="blue">情绪: {backgroundEmotion}</Tag>
          </Space>
        }
        extra={
          <Space>
            <Input.Password
              placeholder="输入 Gemini API Key"
              prefix={<KeyOutlined />}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              style={{ width: 320 }}
              visibilityToggle
            />
            <Button onClick={saveApiKey}>保存</Button>
            <Tooltip title={`可选情绪: ${EMOTIONS.join(", ")}`}>
              <Tag>共 {EMOTIONS.length} 种</Tag>
            </Tooltip>
          </Space>
        }
        style={{ height: "100%" }}
        bodyStyle={{ padding: 0, height: "calc(100% - 57px)" }}
      >
        <div
          style={{
            position: "relative",
            height: "100%",
            backgroundImage: `url(${bgUrl})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(255,255,255,0.35)",
              backdropFilter: "blur(2px)",
            }}
          />

          <div
            style={{
              position: "relative",
              height: "100%",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
              <List
                dataSource={messages}
                renderItem={(m) => (
                  <List.Item style={{ border: "none", padding: "8px 0" }}>
                    <div
                      style={{
                        maxWidth: "70%",
                        marginLeft: m.role === "assistant" ? 0 : "auto",
                        background: m.role === "assistant" ? "rgba(255,255,255,0.95)" : "rgba(24,144,255,0.9)",
                        color: m.role === "assistant" ? "#000" : "#fff",
                        padding: "12px 16px",
                        borderRadius: 18,
                        border: m.role === "assistant" ? "1px solid #f0f0f0" : "none",
                        boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                      }}
                    >
                      <Paragraph style={{ margin: 0, color: m.role === "assistant" ? undefined : "#fff" }}>
                        {m.content}
                      </Paragraph>
                      {m.role === "assistant" && m.emotion && (
                        <div style={{ marginTop: 6 }}>
                          <Tag color="geekblue">emotion: {m.emotion}</Tag>
                        </div>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            </div>

            <div style={{ padding: 12, background: "rgba(255,255,255,0.9)", borderTop: "1px solid #f0f0f0" }}>
              <Space.Compact style={{ width: "100%" }}>
                <TextArea
                  ref={inputRef}
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  placeholder="输入消息...(Enter发送，Shift+Enter换行)"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                />
                <Button type="primary" icon={<SendOutlined />} loading={sending} onClick={handleSend} disabled={!input.trim()}>
                  发送
                </Button>
              </Space.Compact>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
