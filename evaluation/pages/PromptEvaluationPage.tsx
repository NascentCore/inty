import React, { useState, useCallback } from "react";
import { Layout, Typography, Button, message } from "antd";
import { PlusOutlined, PlayCircleOutlined } from "@ant-design/icons";
import { MessageEditor } from "../components/prompt_evaluation/MessageEditor";
import { VariableEditor } from "../components/prompt_evaluation/VariableEditor";
import { OutputDisplay } from "../components/prompt_evaluation/OutputDisplay";

const { Title, Text } = Typography;

export interface Message {
  id: string;
  role: "system" | "assistant" | "user";
  content: string;
}

export interface VariableSet {
  id: string;
  variables: Record<string, string>;
}

const PromptEvaluationPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "system",
      content: "You are a helpful assistant.",
    },
    {
      id: "2",
      role: "user",
      content: "Please write a helpful tip about prompt engineering in 3 sentences or less.",
    },
  ]);

  const [variableSets, setVariableSets] = useState<VariableSet[]>([
    { id: "1", variables: {} },
  ]);

  const [outputs, setOutputs] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  // 添加新消息
  const addMessage = useCallback(() => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: "",
    };
    setMessages([...messages, newMessage]);
  }, [messages]);

  // 删除消息
  const deleteMessage = useCallback((id: string) => {
    if (messages.length > 1) {
      setMessages(messages.filter(msg => msg.id !== id));
    } else {
      message.warning("至少需要保留一条消息");
    }
  }, [messages]);

  // 复制消息
  const copyMessage = useCallback((id: string) => {
    const msg = messages.find(msg => msg.id === id);
    if (msg) {
      navigator.clipboard.writeText(msg.content);
      message.success("消息内容已复制到剪贴板");
    }
  }, [messages]);

  // 更新消息
  const updateMessage = useCallback((id: string, updates: Partial<Message>) => {
    setMessages(messages.map(msg => 
      msg.id === id ? { ...msg, ...updates } : msg
    ));
  }, [messages]);

  // 重新排序消息
  const reorderMessages = useCallback((fromIndex: number, toIndex: number) => {
    const newMessages = [...messages];
    const [removed] = newMessages.splice(fromIndex, 1);
    newMessages.splice(toIndex, 0, removed);
    setMessages(newMessages);
  }, [messages]);

  // 添加变量集
  const addVariableSet = useCallback(() => {
    const newSet: VariableSet = {
      id: Date.now().toString(),
      variables: {},
    };
    setVariableSets([...variableSets, newSet]);
  }, [variableSets]);

  // 删除变量集
  const deleteVariableSet = useCallback((id: string) => {
    if (variableSets.length > 1) {
      setVariableSets(variableSets.filter(set => set.id !== id));
    } else {
      message.warning("至少需要保留一个变量集");
    }
  }, [variableSets]);

  // 更新变量
  const updateVariable = useCallback((setId: string, key: string, value: string) => {
    setVariableSets(variableSets.map(set => {
      if (set.id === setId) {
        return {
          ...set,
          variables: { ...set.variables, [key]: value },
        };
      }
      return set;
    }));
  }, [variableSets]);

  // 删除变量
  const deleteVariable = useCallback((setId: string, key: string) => {
    setVariableSets(variableSets.map(set => {
      if (set.id === setId) {
        const newVariables = { ...set.variables };
        delete newVariables[key];
        return { ...set, variables: newVariables };
      }
      return set;
    }));
  }, [variableSets]);

  // 添加变量
  const addVariable = useCallback((setId: string) => {
    setVariableSets(variableSets.map(set => {
      if (set.id === setId) {
        return {
          ...set,
          variables: { ...set.variables, [`var_${Date.now()}`]: "" },
        };
      }
      return set;
    }));
  }, [variableSets]);

  // 运行提示词
  const runPrompt = useCallback(async () => {
    setIsRunning(true);
    try {
      // 这里将来会调用 OpenRouter API
      // 暂时模拟响应
      await new Promise(resolve => setTimeout(resolve, 1000));
      const mockResponse = "这是一个模拟的 AI 响应，用于演示功能。";
      setOutputs([mockResponse]);
      message.success("提示词执行成功");
    } catch (error) {
      message.error("执行失败，请检查提示词格式");
    } finally {
      setIsRunning(false);
    }
  }, [messages, variableSets]);

  // 将输出添加到下一轮
  const addOutputToNextRound = useCallback((output: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role: "assistant",
      content: output,
    };
    setMessages([...messages, newMessage]);
    message.success("输出已添加到下一轮对话");
  }, [messages]);

  return (
    <div style={{ padding: "24px", height: "100vh", overflow: "hidden" }}>
      <Layout style={{ height: "calc(100vh - 48px)", background: "transparent" }}>
        {/* 左侧：提示词编辑区域 */}
        <div id="prompt-editor" style={{ width: "800px", flex: 1, overflow: "auto" }}>
          <div style={{ background: "#fff", borderRadius: "8px", padding: "24px" }}>
            <div style={{ marginBottom: "24px" }}>
              <Title level={4} style={{ margin: 0, color: "#1890ff" }}>
                提示词模板
              </Title>
              <Text type="secondary">
                编辑符合 OpenAI Chat API 标准的消息序列
              </Text>
            </div>

            {/* 消息编辑器列表 */}
            <div style={{ width: "50%", marginBottom: "24px" }}>
              {messages.map((message, index) => (
                <MessageEditor
                  key={message.id}
                  message={message}
                  index={index}
                  onUpdate={(updates) => updateMessage(message.id, updates)}
                  onDelete={() => deleteMessage(message.id)}
                  onCopy={() => copyMessage(message.id)}
                  onReorder={reorderMessages}
                  isSelected={false}
                />
              ))}
            </div>

            {/* 添加新消息按钮 */}
            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={addMessage}
              style={{ width: "50%", height: "60px" }}
            >
              添加新消息
            </Button>
          </div>
        </div>

        {/* 右侧：变量设置、执行按钮和输出区域 */}
        <div id="variable-editor" style={{ width: "400px", display: "flex", flexDirection: "column", marginLeft: "auto" }}>
          {/* 变量编辑器 */}
          <div style={{ background: "#fff", borderRadius: "8px", padding: "24px", marginBottom: "24px" }}>
            <VariableEditor
              variableSets={variableSets}
              onAddSet={addVariableSet}
              onDeleteSet={deleteVariableSet}
              onUpdateVariable={updateVariable}
              onDeleteVariable={deleteVariable}
              onAddVariable={addVariable}
            />
          </div>

          {/* 执行按钮 */}
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={runPrompt}
            loading={isRunning}
            size="large"
            style={{ marginBottom: "24px", height: "48px" }}
          >
            执行 (⌘⏎)
          </Button>

          {/* 输出显示区域 */}
          <div style={{ background: "#fff", borderRadius: "8px", padding: "24px", flex: 1 }}>
            <OutputDisplay
              outputs={outputs}
              onAddToNextRound={addOutputToNextRound}
            />
          </div>
        </div>
      </Layout>
    </div>
  );
};

export default PromptEvaluationPage;
