/**
 * 评测页面 - 整合所有评测功能的主页面
 * 包含配置、智能体选择、问题管理、监控等功能
 */

import React, { useState, useCallback, useEffect } from "react";
import {
  Layout,
  Steps,
  Button,
  Card,
  Space,
  message,
  Modal,
  Alert,
  Divider,
  Typography,
  Row,
  Col,
} from "antd";
import {
  SettingOutlined,
  RobotOutlined,
  QuestionCircleOutlined,
  PlayCircleOutlined,
  SaveOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { TestConfigForm } from "../components/evaluation/TestConfigForm";
import { AgentSelector } from "../components/evaluation/AgentSelector";
import { QuestionManager } from "../components/evaluation/QuestionManager";
import { EvaluationMonitor } from "../components/evaluation/EvaluationMonitor";
import { useEvaluationSession } from "../hooks/useEvaluationSession";
import type { EvaluationSessionCreateRequest } from "../types";
import { formatUtcTime } from "../utils/dateUtils";

const { Content } = Layout;
const { Title, Text } = Typography;

interface StepStatus {
  config: boolean;
  agents: boolean;
  questions: boolean;
  ready: boolean;
}

export const EvaluationPage: React.FC = () => {
  // 步骤状态
  const [currentStep, setCurrentStep] = useState(0);
  const [stepStatus, setStepStatus] = useState<StepStatus>({
    config: false,
    agents: false,
    questions: false,
    ready: false,
  });

  // 表单数据
  const [configData, setConfigData] = useState<
    Partial<EvaluationSessionCreateRequest>
  >({});
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [questions, setQuestions] = useState<string[]>([]);
  const [isConfigValid, setIsConfigValid] = useState(false);

  // 评测会话管理
  const { session, createSession, startSession, loading, error } =
    useEvaluationSession();

  // 步骤配置
  const steps = [
    {
      title: "基础配置",
      icon: <SettingOutlined />,
      description: "设置测试名称、评分模型等基本信息",
    },
    {
      title: "选择智能体",
      icon: <RobotOutlined />,
      description: "选择需要参与评测的智能体",
    },
    {
      title: "管理问题",
      icon: <QuestionCircleOutlined />,
      description: "添加或导入测试问题",
    },
    {
      title: "开始评测",
      icon: <PlayCircleOutlined />,
      description: "启动评测并监控进度",
    },
  ];

  // 更新步骤状态
  useEffect(() => {
    const newStatus: StepStatus = {
      config: isConfigValid && !!configData.name && !!configData.scoring_model,
      agents: selectedAgents.length > 0,
      questions: questions.length > 0,
      ready: false,
    };

    newStatus.ready =
      newStatus.config && newStatus.agents && newStatus.questions;

    setStepStatus(newStatus);
  }, [isConfigValid, configData, selectedAgents, questions]);

  // 表单数据变化处理
  const handleConfigChange = useCallback(
    (values: Partial<EvaluationSessionCreateRequest>) => {
      setConfigData(values);
    },
    [],
  );

  const handleAgentsChange = useCallback((agents: string[]) => {
    setSelectedAgents(agents);
  }, []);

  const handleQuestionsChange = useCallback((newQuestions: string[]) => {
    setQuestions(newQuestions);
  }, []);

  // 步骤导航
  const goToStep = useCallback(
    (step: number) => {
      if (step < 0 || step >= steps.length) return;

      // 检查是否可以跳转到该步骤
      if (step > 0 && !stepStatus.config) {
        message.warning("请先完成基础配置");
        return;
      }

      if (step > 1 && !stepStatus.agents) {
        message.warning("请先选择智能体");
        return;
      }

      if (step > 2 && !stepStatus.questions) {
        message.warning("请先添加测试问题");
        return;
      }

      setCurrentStep(step);
    },
    [stepStatus, steps.length],
  );

  const nextStep = useCallback(() => {
    goToStep(currentStep + 1);
  }, [currentStep, goToStep]);

  const prevStep = useCallback(() => {
    goToStep(currentStep - 1);
  }, [currentStep, goToStep]);

  // 创建评测会话
  const handleCreateSession = useCallback(async () => {
    if (!stepStatus.ready) {
      message.error("请完成所有配置步骤");
      return;
    }

    const sessionData: EvaluationSessionCreateRequest = {
      name: configData.name!,
      questions,
      selected_agents: selectedAgents,
      scoring_model: configData.scoring_model!,
      scoring_criteria: configData.scoring_criteria,
      use_new_user_identity: configData.use_new_user_identity || false,
      config: configData.config || {
        agents: [],
        questions: [],
        scoring_model: configData.scoring_model!,
        scoring_criteria: configData.scoring_criteria || "",
        parallel_limit: 1,
        timeout: 300,
      },
    };

    const newSession = await createSession(sessionData);
    if (newSession) {
      message.success("评测会话创建成功，正在启动评测...");
      setCurrentStep(3); // 跳转到监控步骤

      // 立即启动评测
      try {
        await startSession(newSession.id);
        message.success("评测已开始运行");
      } catch (error) {
        console.error("启动评测失败:", error);
        message.error("启动评测失败，请手动点击开始按钮");
      }
    }
  }, [
    stepStatus.ready,
    configData,
    questions,
    selectedAgents,
    createSession,
    startSession,
  ]);

  // 重置所有数据
  const handleReset = useCallback(() => {
    Modal.confirm({
      title: "确认重置",
      content: "确定要重置所有配置吗？这将清除当前的所有设置。",
      okText: "确定",
      cancelText: "取消",
      onOk: () => {
        setCurrentStep(0);
        setConfigData({});
        setSelectedAgents([]);
        setQuestions([]);
        setIsConfigValid(false);
        message.success("配置已重置");
      },
    });
  }, []);

  // 保存草稿
  const handleSaveDraft = useCallback(() => {
    const draft = {
      configData,
      selectedAgents,
      questions,
      timestamp: Date.now(),
    };

    localStorage.setItem("evaluation_draft", JSON.stringify(draft));
    message.success("草稿已保存");
  }, [configData, selectedAgents, questions]);

  // 加载草稿
  const handleLoadDraft = useCallback(() => {
    try {
      const draftStr = localStorage.getItem("evaluation_draft");
      if (!draftStr) {
        message.info("没有找到保存的草稿");
        return;
      }

      const draft = JSON.parse(draftStr);

      Modal.confirm({
        title: "加载草稿",
        content: `发现草稿 (${formatUtcTime(draft.timestamp)})，是否加载？这将覆盖当前配置。`,
        okText: "加载",
        cancelText: "取消",
        onOk: () => {
          setConfigData(draft.configData || {});
          setSelectedAgents(draft.selectedAgents || []);
          setQuestions(draft.questions || []);
          message.success("草稿已加载");
        },
      });
    } catch (error) {
      message.error("加载草稿失败");
    }
  }, []);

  // 渲染步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <TestConfigForm
            initialValues={configData}
            onValuesChange={handleConfigChange}
            onValidationChange={setIsConfigValid}
          />
        );

      case 1:
        return (
          <AgentSelector
            selectedAgents={selectedAgents}
            onChange={handleAgentsChange}
            maxSelection={20}
          />
        );

      case 2:
        return (
          <QuestionManager
            questions={questions}
            onChange={handleQuestionsChange}
            maxQuestions={100}
          />
        );

      case 3:
        return (
          <EvaluationMonitor
            session={session}
            onSessionChange={(updatedSession) => {
              // 当EvaluationMonitor通知session状态变化时，不需要特殊处理
              // 因为useEvaluationSession hook会自动管理状态
              console.log("评测会话状态更新:", updatedSession?.status);
            }}
            showControls={true}
            autoRefresh={true}
          />
        );

      default:
        return null;
    }
  };

  // 渲染操作按钮
  const renderStepActions = () => {
    const actions = [];

    // 上一步按钮
    if (currentStep > 0 && currentStep < 3) {
      actions.push(
        <Button key="prev" onClick={prevStep}>
          上一步
        </Button>,
      );
    }

    // 下一步/创建按钮
    if (currentStep < 2) {
      const canNext =
        (currentStep === 0 && stepStatus.config) ||
        (currentStep === 1 && stepStatus.agents) ||
        (currentStep === 2 && stepStatus.questions);

      actions.push(
        <Button
          key="next"
          type="primary"
          onClick={nextStep}
          disabled={!canNext}
        >
          下一步
        </Button>,
      );
    } else if (currentStep === 2) {
      actions.push(
        <Button
          key="create"
          type="primary"
          onClick={handleCreateSession}
          disabled={!stepStatus.ready}
          loading={loading}
          icon={<PlayCircleOutlined />}
        >
          创建并开始评测
        </Button>,
      );
    }

    return actions;
  };

  return (
    <Layout className="evaluation-page">
      <Content style={{ padding: "24px", background: "#f0f2f5" }}>
        {/* 页面标题已移除，使用顶部导航栏 */}

        {/* 步骤指示器 */}
        <Card style={{ marginBottom: 24 }}>
          <Steps
            current={currentStep}
            items={steps.map((step, index) => ({
              ...step,
              status:
                index === currentStep
                  ? "process"
                  : index < currentStep ||
                      (index === 0 && stepStatus.config) ||
                      (index === 1 && stepStatus.agents) ||
                      (index === 2 && stepStatus.questions) ||
                      (index === 3 && session)
                    ? "finish"
                    : "wait",
            }))}
            onChange={goToStep}
          />
        </Card>

        {/* 错误提示 */}
        {error && (
          <Alert
            message="操作失败"
            description={error}
            type="error"
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 步骤内容 */}
        <div style={{ marginBottom: 24 }}>{renderStepContent()}</div>

        {/* 操作栏 */}
        <Card>
          <Row justify="space-between" align="middle">
            <Col>
              <Space>
                <Button
                  icon={<SaveOutlined />}
                  onClick={handleSaveDraft}
                  disabled={currentStep === 3}
                >
                  保存草稿
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleLoadDraft}
                  disabled={currentStep === 3}
                >
                  加载草稿
                </Button>
                <Button
                  danger
                  onClick={handleReset}
                  disabled={currentStep === 3 && session?.status === "running"}
                >
                  重置配置
                </Button>
              </Space>
            </Col>
            <Col>
              <Space>{renderStepActions()}</Space>
            </Col>
          </Row>

          {/* 配置摘要 */}
          {(stepStatus.config || stepStatus.agents || stepStatus.questions) &&
            currentStep < 3 && (
              <>
                <Divider />
                <div>
                  <Title level={5}>当前配置摘要</Title>
                  <Row gutter={[16, 8]}>
                    {stepStatus.config && (
                      <Col span={8}>
                        <Text type="secondary">评测名称: </Text>
                        <Text strong>{configData.name}</Text>
                      </Col>
                    )}
                    {stepStatus.agents && (
                      <Col span={8}>
                        <Text type="secondary">选中智能体: </Text>
                        <Text strong>{selectedAgents.length}个</Text>
                      </Col>
                    )}
                    {stepStatus.questions && (
                      <Col span={8}>
                        <Text type="secondary">测试问题: </Text>
                        <Text strong>{questions.length}个</Text>
                      </Col>
                    )}
                  </Row>
                </div>
              </>
            )}
        </Card>
      </Content>
    </Layout>
  );
};
