/**
 * 评测配置表单组件
 * 负责评测会话的基本配置（测试名称、用户身份、评分标准等）
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Checkbox,
  Select,
  Button,
  Alert,
  Space,
  Tooltip,
} from 'antd';
import {
  InfoCircleOutlined,
  QuestionCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useForm } from '../../hooks/useForm';
import api from '../../services/api';
import modelCacheService from '../../services/modelCache';
import type { 
  EvaluationSessionCreateRequest, 
  ScoringModel,
  ValidationError 
} from '../../types';

const { TextArea } = Input;
const { Option } = Select;

interface TestConfigFormProps {
  initialValues?: Partial<EvaluationSessionCreateRequest>;
  onValuesChange?: (values: Partial<EvaluationSessionCreateRequest>) => void;
  onValidationChange?: (isValid: boolean) => void;
}

interface FormValues extends EvaluationSessionCreateRequest {
  // 添加一些UI专用字段
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
  const [scoringModels, setScoringModels] = useState<ScoringModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  // 表单验证
  const validateForm = (values: FormValues): ValidationError[] => {
    const errors: ValidationError[] = [];

    if (!values.name?.trim()) {
      errors.push({ field: 'name', message: '请输入测试名称' });
    }

    if (!values.questions || values.questions.length === 0) {
      errors.push({ field: 'questions', message: '请添加至少一个测试问题' });
    }

    if (!values.selected_agents || values.selected_agents.length === 0) {
      errors.push({ field: 'selected_agents', message: '请选择至少一个智能体' });
    }

    if (!values.scoring_model) {
      errors.push({ field: 'scoring_model', message: '请选择评分模型' });
    }

    return errors;
  };

  // 表单Hook
  const form = useForm<FormValues>({
    initialValues: {
      name: `智能体评测 - ${new Date().toLocaleString()}`,
      questions: [],
      selected_agents: [],
      scoring_model: '',
      scoring_criteria: defaultScoringCriteria,
      use_new_user_identity: false,
      config: {},
      ...initialValues,
    },
    validate: validateForm,
  });

  // 加载评分模型 - 使用缓存服务
  const loadScoringModels = async (forceRefresh = false) => {
    try {
      setModelsLoading(true);
      console.log('正在加载评分模型...');
      const models = await modelCacheService.getScoringModels(forceRefresh);
      
      setScoringModels(models);
      console.log('评分模型加载成功:', models.length, '个');
      
      // 设置默认模型
      if (models.length > 0 && !form.values.scoring_model) {
        form.setValue('scoring_model', models[0].id);
      }
    } catch (error) {
      console.error('加载评分模型失败:', error);
    } finally {
      setModelsLoading(false);
      console.log('评分模型加载状态已重置');
    }
  };

  // 刷新模型列表
  const handleRefreshModels = () => {
    loadScoringModels(true);
  };

  useEffect(() => {
    // 防止重复调用
    if (scoringModels.length > 0) {
      console.log('评分模型已加载，跳过重复请求');
      return;
    }
    
    loadScoringModels();
  }, []); // 保持空依赖数组，只在组件挂载时运行一次

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
          validateStatus={form.hasFieldError('name') ? 'error' : ''}
          help={form.getFieldError('name')}
        >
          <Input
            value={form.values.name}
            onChange={(e) => form.setValue('name', e.target.value)}
            placeholder="请输入测试名称"
            size="large"
          />
        </Form.Item>

        {/* 用户身份选择 */}
        <Form.Item label="用户身份">
          <Checkbox
            checked={form.values.use_new_user_identity}
            onChange={(e) => form.setValue('use_new_user_identity', e.target.checked)}
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
          validateStatus={form.hasFieldError('scoring_model') ? 'error' : ''}
          help={form.getFieldError('scoring_model')}
        >
          <div style={{ display: 'flex', gap: 8 }}>
            <Select
              style={{ flex: 1 }}
              value={form.values.scoring_model}
              onChange={(value) => form.setValue('scoring_model', value)}
              placeholder="选择评分模型"
              size="large"
              loading={modelsLoading}
              dropdownStyle={{ maxHeight: 400, overflow: 'auto' }}
              optionLabelProp="label"
              showSearch
              filterOption={(input, option) => {
                const modelName = option?.label || '';
                const modelDescription = option?.children?.props?.children?.[1] || '';
                const searchText = input.toLowerCase();
                return (
                  modelName.toLowerCase().includes(searchText) ||
                  String(modelDescription).toLowerCase().includes(searchText)
                );
              }}
            >
              {scoringModels.map((model) => (
                <Option 
                  key={model.id} 
                  value={model.id}
                  label={model.name}
                >
                  <div style={{ padding: '4px 0' }}>
                    <div style={{ 
                      fontWeight: 'bold', 
                      marginBottom: '4px',
                      whiteSpace: 'normal',
                      wordBreak: 'break-word'
                    }}>
                      {model.name}
                    </div>
                    {model.description && (
                      <div style={{ 
                        fontSize: '12px', 
                        color: '#666',
                        whiteSpace: 'normal',
                        wordBreak: 'break-word',
                        lineHeight: '1.4',
                        maxHeight: '60px',
                        overflow: 'hidden',
                      }}>
                        {model.description.length > 100 
                          ? `${model.description.substring(0, 100)}...` 
                          : model.description
                        }
                      </div>
                    )}
                  </div>
                </Option>
              ))}
            </Select>
            <Button
              icon={<SyncOutlined />}
              size="large"
              onClick={handleRefreshModels}
              loading={modelsLoading}
              title="刷新模型列表"
            />
          </div>
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
            onChange={(e) => form.setValue('scoring_criteria', e.target.value)}
            placeholder="请输入评分标准，用于指导大模型进行评分"
            rows={8}
            showCount
            maxLength={5000}
          />
          
          <div style={{ marginTop: 8 }}>
            <Button
              type="link"
              size="small"
              onClick={() => form.setValue('scoring_criteria', defaultScoringCriteria)}
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