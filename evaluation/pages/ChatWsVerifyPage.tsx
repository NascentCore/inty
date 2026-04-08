/**
 * WebSocket 对话验证页：连接 /api/v1/chat/ws（与生产一致）。
 * 超级用户在页头选择 Assume user 时，URL 会带 assume_user_id，与 HTTP X-Assume-User-Id 对齐。
 */

import React, { useState, useRef, useCallback } from "react";
import {
  Layout,
  Card,
  Input,
  Button,
  Space,
  Typography,
  List,
  Avatar,
  Tag,
  message as antMessage,
} from "antd";
import {
  SendOutlined,
  DisconnectOutlined,
  ApiOutlined,
} from "@ant-design/icons";
import type { Agent } from "../types";
import { SingleAgentSelectorPanel } from "../components/common/SingleAgentSelectorPanel";
import { AvatarDisplay } from "../components/common/AvatarDisplay";
import { getChatWebSocketUrl, getGlobalApiKey } from "../services/api";

const { Content } = Layout;
const { Text } = Typography;
const { TextArea } = Input;

interface VerifyMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  error?: string;
}

export const ChatWsVerifyPage: React.FC = () => {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<VerifyMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    if (!getGlobalApiKey()?.trim()) {
      antMessage.warning("请先设置 API Key");
      return;
    }
    const url = getChatWebSocketUrl();
    const ws = new WebSocket(url);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
    };
    ws.onerror = () => {
      antMessage.error("WebSocket 连接错误");
    };
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data as string) as {
          code?: number;
          message?: string;
          data?: { choices?: Array<{ message?: { content?: string } }> };
          agent_id?: string;
        };
        if (payload.code !== 200) {
          setMessages((prev) =>
            prev.concat({
              id: `err-${Date.now()}`,
              role: "assistant",
              content: "",
              error: payload.message ?? "Unknown error",
            }),
          );
          setSending(false);
          return;
        }
        const content =
          payload.data?.choices?.[0]?.message?.content ?? payload.message ?? "";
        setMessages((prev) =>
          prev.concat({
            id: `ai-${Date.now()}`,
            role: "assistant",
            content,
          }),
        );
      } catch {
        setMessages((prev) =>
          prev.concat({
            id: `err-${Date.now()}`,
            role: "assistant",
            content: "",
            error: "Invalid response",
          }),
        );
      }
      setSending(false);
    };
    wsRef.current = ws;
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  const sendMessage = useCallback(() => {
    const text = inputValue.trim();
    if (
      !text ||
      !selectedAgent ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN
    ) {
      if (!selectedAgent) antMessage.warning("请先选择角色");
      else if (!connected) antMessage.warning("请先连接 WebSocket");
      return;
    }
    setSending(true);
    setInputValue("");
    setMessages((prev) =>
      prev.concat({ id: `user-${Date.now()}`, role: "user", content: text }),
    );
    const payload = {
      agent_id: selectedAgent.id,
      request: {
        messages: [{ role: "user" as const, content: text }],
        stream: false,
        model: "chatbot",
        language: "zh",
      },
    };
    wsRef.current.send(JSON.stringify(payload));
  }, [inputValue, selectedAgent, connected]);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Content style={{ padding: 24 }}>
        <Card
          title={
            <Space>
              <ApiOutlined />
              <span>WebSocket 对话验证</span>
              <Tag color="red">生产 WS，会落库</Tag>
            </Space>
          }
        >
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Space wrap>
              <Button
                type="primary"
                onClick={connect}
                disabled={connected}
                icon={<ApiOutlined />}
              >
                连接
              </Button>
              <Button
                onClick={disconnect}
                disabled={!connected}
                icon={<DisconnectOutlined />}
              >
                断开
              </Button>
              <Text type={connected ? "success" : "secondary"}>
                {connected ? "已连接" : "未连接"}
              </Text>
            </Space>

            <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
              <div style={{ minWidth: 280, maxWidth: 360 }}>
                <Text strong>选择角色</Text>
                <div style={{ marginTop: 8 }}>
                  <SingleAgentSelectorPanel
                    selectedAgentId={selectedAgent?.id}
                    onSelectAgent={setSelectedAgent}
                  />
                </div>
              </div>

              <div style={{ flex: 1, minWidth: 300 }}>
                <Text strong>对话（仅展示本次连接内收发）</Text>
                <Card
                  size="small"
                  style={{ marginTop: 8, maxHeight: 400, overflow: "auto" }}
                >
                  {messages.length === 0 ? (
                    <Text type="secondary">发送消息后，AI 回复将显示在此</Text>
                  ) : (
                    <List
                      dataSource={messages}
                      renderItem={(item) => (
                        <List.Item>
                          <List.Item.Meta
                            avatar={
                              item.role === "user" ? (
                                <Avatar icon={<span>U</span>} />
                              ) : selectedAgent ? (
                                <AvatarDisplay
                                  agent={selectedAgent}
                                  size={32}
                                />
                              ) : (
                                <Avatar icon={<span>A</span>} />
                              )
                            }
                            title={item.role === "user" ? "用户" : "助手"}
                            description={item.error ?? (item.content || "(空)")}
                          />
                        </List.Item>
                      )}
                    />
                  )}
                </Card>
                <Space.Compact style={{ width: "100%", marginTop: 8 }}>
                  <TextArea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="输入消息..."
                    autoSize={{ minRows: 1, maxRows: 4 }}
                    onPressEnter={(e) => {
                      if (!e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                  />
                  <Button
                    type="primary"
                    onClick={sendMessage}
                    loading={sending}
                    disabled={!connected || !selectedAgent}
                    icon={<SendOutlined />}
                  >
                    发送
                  </Button>
                </Space.Compact>
              </div>
            </div>
          </Space>
        </Card>
      </Content>
    </Layout>
  );
};
