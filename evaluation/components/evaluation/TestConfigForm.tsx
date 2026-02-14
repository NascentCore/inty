/**
 * 评测配置表单组件
 * 负责评测会话的基本配置（测试名称、用户身份、评分标准等）
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  Form,
  Input,
  Checkbox,
  Button,
  Alert,
  Space,
  Tooltip,
} from "antd";
import { InfoCircleOutlined, QuestionCircleOutlined } from "@ant-design/icons";
import { useForm } from "../../hooks/useForm";
import modelCacheService from "../../services/modelCache";
import { ModelSelector } from "../common/ModelSelector";
import { formatUtcTimeRaw } from "../../utils/dateUtils";
import type {
  EvaluationSessionCreateRequest,
  OpenRouterModel,
  ValidationError,
} from "../../types";

const { TextArea } = Input;

interface TestConfigFormProps {
  initialValues?: Partial<EvaluationSessionCreateRequest>;
  onValuesChange?: (values: Partial<EvaluationSessionCreateRequest>) => void;
  onValidationChange?: (isValid: boolean) => void;
}

interface FormValues {
  name: string;
  questions: string[];
  selected_agents: string[];
  scoring_model: string;
  scoring_criteria: string;
  use_new_user_identity: boolean;
  config: EvaluationSessionCreateRequest["config"];
}

const defaultScoringCriteria = `请基于智能体的角色设定对其表现进行综合评分(1-10分):

评分维度：
1. 角色一致性 (1-10分) - 回答是否符合角色设定和人设，是否保持角色特征
2. 表达自然度 (1-10分) - 语言表达是否自然流畅，符合角色的说话风格
3. 情境适应性 (1-10分) - 是否能够适当回应问题情境，展现角色应有的反应
4. 创意表现力 (1-10分) - 是否有创意和个性化的表达，避免机械化回复

评分说明：
- 请结合智能体的角色设定（姓名、性别、简介、提示词等）进行评价
- 重点关注角色扮演的真实性和一致性，而非传统AI助手的标准
- 每个维度给出具体分数和详细理由
- 最后给出综合评分和总体评价`;

export const TestConfigForm: React.FC<TestConfigFormProps> = ({
  initialValues = {},
  onValuesChange,
  onValidationChange,
}) => {
  // 状态管理
  const [scoringModels, setScoringModels] = useState<OpenRouterModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  // 表单验证
  const validateForm = (values: FormValues): ValidationError[] => {
    const errors: ValidationError[] = [];

    if (!values.name?.trim()) {
      errors.push({ field: "name", message: "请输入测试名称" });
    }

    if (!values.questions || values.questions.length === 0) {
      errors.push({ field: "questions", message: "请添加至少一个测试问题" });
    }

    if (!values.selected_agents || values.selected_agents.length === 0) {
      errors.push({
        field: "selected_agents",
        message: "请选择至少一个智能体",
      });
    }

    if (!values.scoring_model) {
      errors.push({ field: "scoring_model", message: "请选择评分模型" });
    }

    return errors;
  };

  // 表单Hook
  const form = useForm<FormValues>({
    initialValues: {
      name: `智能体评测 - ${formatUtcTimeRaw(new Date())}`,
      questions: [],
      selected_agents: [],
      scoring_model: "",
      scoring_criteria: defaultScoringCriteria,
      use_new_user_identity: false,
      config: {
        agents: [],
        questions: [],
        scoring_model: "",
        scoring_criteria: defaultScoringCriteria,
        parallel_limit: 1,
        timeout: 300,
      },
      ...initialValues,
    },
    validate: validateForm,
  });
  const scoringModelValue = form.values.scoring_model;
  const setFormValue = form.setValue;

  // 加载评分模型 - 使用OpenRouter模型
  const loadScoringModels = useCallback(
    async (currentScoringModel: string) => {
      try {
        setModelsLoading(true);
        const models = await modelCacheService.getOpenRouterModels();

        setScoringModels(models);

        // 设置默认模型 - 优先选择 google/gemini-2.5-flash-lite
        if (models.length > 0 && !currentScoringModel) {
          const preferredModel = models.find(
            (model) => model.id === "google/gemini-2.5-flash-lite",
          );
          const defaultModel = preferredModel || models[0];
          setFormValue("scoring_model", defaultModel.id);
        }
      } catch (error) {
        console.error("加载评分模型失败:", error);
      } finally {
        setModelsLoading(false);
      }
    },
    [setFormValue],
  );

  // 刷新模型列表
  const handleRefreshModels = () => {
    loadScoringModels(scoringModelValue);
  };

  useEffect(() => {
    // 防止重复调用
    if (scoringModels.length > 0) {
      return;
    }

    loadScoringModels(scoringModelValue);
  }, [loadScoringModels, scoringModels.length, scoringModelValue]);

  // 通知父组件表单值变化
  useEffect(() => {
    onValuesChange?.(form.values);
  }, [form.values, onValuesChange]);

  // 通知父组件验证状态变化
  useEffect(() => {
    onValidationChange?.(form.isValid);
  }, [form.isValid, onValidationChange]);

  return (
    <Card title="测试配置" className="test-config-form">
      <Form layout="vertical" onFinish={form.handleSubmit}>
        {/* 测试名称 */}
        <Form.Item
          label="测试名称"
          required
          validateStatus={form.hasFieldError("name") ? "error" : ""}
          help={form.getFieldError("name")}
        >
          <Input
            value={form.values.name}
            onChange={(e) => form.setValue("name", e.target.value)}
            placeholder="请输入测试名称"
            size="large"
          />
        </Form.Item>

        {/* 用户身份选择 */}
        <Form.Item label="用户身份">
          <Checkbox
            checked={form.values.use_new_user_identity}
            onChange={(e) =>
              form.setValue("use_new_user_identity", e.target.checked)
            }
          >
            以新用户身份发起测试
            <Tooltip title="将创建新的游客账户进行测试，测试结果将显示游客身份信息">
              <QuestionCircleOutlined style={{ marginLeft: 4 }} />
            </Tooltip>
          </Checkbox>

          {form.values.use_new_user_identity ? (
            <Alert
              message="✓ 将创建新的游客账户进行测试，测试结果将显示游客身份信息"
              type="success"
              showIcon
              style={{ marginTop: 8 }}
            />
          ) : (
            <Alert
              message="使用后端配置的默认用户身份进行测试"
              type="info"
              style={{ marginTop: 8 }}
            />
          )}
        </Form.Item>

        {/* 评分模型 */}
        <Form.Item
          label={
            <Space>
              评分模型
              <Tooltip title="选择用于自动评分的LLM模型">
                <InfoCircleOutlined />
              </Tooltip>
            </Space>
          }
          required
          validateStatus={form.hasFieldError("scoring_model") ? "error" : ""}
          help={form.getFieldError("scoring_model")}
        >
          <ModelSelector
            name="scoring_model"
            label=""
            rules={[{ required: true, message: "请选择评分模型" }]}
            value={form.values.scoring_model}
            onChange={(value) => form.setValue("scoring_model", value)}
            models={scoringModels}
            loading={modelsLoading}
            onRefresh={handleRefreshModels}
            placeholder="选择用于自动评分的LLM模型"
            style={{ width: "100%" }}
          />
        </Form.Item>

        {/* 评分标准 */}
        <Form.Item
          label={
            <Space>
              评分标准
              <Tooltip title="用于指导LLM进行评分的详细标准和要求">
                <InfoCircleOutlined />
              </Tooltip>
            </Space>
          }
        >
          <TextArea
            value={form.values.scoring_criteria}
            onChange={(e) => form.setValue("scoring_criteria", e.target.value)}
            placeholder="请输入评分标准，用于指导大模型进行评分"
            rows={8}
            showCount
            maxLength={5000}
          />

          <div style={{ marginTop: 8 }}>
            <Button
              type="link"
              size="small"
              onClick={() =>
                form.setValue("scoring_criteria", defaultScoringCriteria)
              }
            >
              恢复默认评分标准
            </Button>
          </div>
        </Form.Item>

        {/* 高级配置 */}
        <Form.Item label="高级配置">
          <Alert
            message="高级配置将在后续版本中提供更多选项"
            type="info"
            showIcon
          />
        </Form.Item>
      </Form>
    </Card>
  );
};
