/**
 * 通用 API 测试包装组件
 * 用于统一 DevTest 页面中的测试组件样式和逻辑
 */

import { Button, Input, message, Space } from 'antd';
import React, { useCallback, useState } from 'react';
import { logger } from '@/utils/logger';
import { handleTestError } from '@/utils/testError';
import './index.less';

/**
 * 输入框配置接口
 */
export interface ITestInput {
  /** 字段名称（作为表单字段的 key） */
  name: string;
  /** 显示标签 */
  label: string;
  /** 是否必填 */
  required?: boolean;
  /** 输入框类型 */
  type?: 'text' | 'number' | 'password' | 'select';
  /** 占位提示文本 */
  placeholder?: string;
  /** 默认值 */
  defaultValue?: string;
  /** 多行输入 */
  multiline?: boolean;
  /** 多行输入行数 */
  rows?: number;
  /** 下拉选项（仅 type='select' 时使用） */
  options?: Array<{ label: string; value: string }>;
}

/**
 * TestWrapper 组件属性接口
 */
export interface ITestWrapperProps<T = Record<string, string>, R = unknown> {
  /** 测试标题 */
  title: string;
  /** 输入框配置列表 */
  inputs?: ITestInput[];
  /** 测试执行函数 */
  onTest: (values: T) => Promise<R>;
  /** 测试成功回调 */
  onSuccess?: (response: R) => void;
  /** 自定义结果渲染 */
  renderResult?: (response: R) => React.ReactNode;
  /** 按钮文本 */
  buttonText?: string;
  /** 按钮类型 */
  buttonType?: 'default' | 'primary' | 'dashed' | 'link' | 'text';
  /** 按钮危险样式 */
  buttonDanger?: boolean;
  /** 额外的组件说明 */
  description?: string;
  /** 是否在测试前验证必填项 */
  validateRequired?: boolean;
  /** 自定义请求参数日志输出 */
  logParams?: (values: T) => void;
  /** 自定义成功日志输出 */
  logSuccess?: (response: R) => void;
}

/**
 * 通用测试组件
 */
function TestWrapper<T = Record<string, string>, R = unknown>(
  props: ITestWrapperProps<T, R>,
): React.ReactElement {
  const {
    title,
    inputs = [],
    onTest,
    onSuccess,
    renderResult,
    buttonText = '执行测试',
    buttonType = 'primary',
    buttonDanger = false,
    description,
    validateRequired = true,
    logParams,
    logSuccess,
  } = props;

  const [loading, setLoading] = useState(false);
  const [values, setValues] = useState<Record<string, string>>(() => {
    const initialValues: Record<string, string> = {};
    inputs.forEach((input) => {
      if (input.defaultValue) {
        initialValues[input.name] = input.defaultValue;
      }
    });
    return initialValues;
  });
  const [result, setResult] = useState<R | null>(null);

  /**
   * 更新输入框值
   */
  const handleInputChange = useCallback((name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  }, []);

  /**
   * 验证必填项
   */
  const validateInputs = useCallback((): boolean => {
    if (!validateRequired) return true;

    for (const input of inputs) {
      if (input.required && !values[input.name]?.trim()) {
        message.warning(`请输入${input.label}`);
        return false;
      }
    }
    return true;
  }, [inputs, values, validateRequired]);

  /**
   * 执行测试
   */
  const handleTest = useCallback(async () => {
    // 验证输入
    if (!validateInputs()) {
      return;
    }

    setLoading(true);
    setResult(null);

    // 开始测试日志
    logger.test(`开始测试: ${title}`);

    try {
      // 输出请求参数
      if (logParams) {
        logParams(values as T);
      } else if (inputs.length > 0) {
        logger.testDetail('请求参数', values);
      }

      // 执行测试
      const response = await onTest(values as T);

      // 输出成功日志
      if (logSuccess) {
        logSuccess(response);
      } else {
        logger.testSuccess(`${title}成功`, response);
      }

      // 显示成功提示
      message.success(`${title}成功`);

      // 保存结果
      setResult(response);

      // 执行成功回调
      onSuccess?.(response);
    } catch (error: unknown) {
      // 统一错误处理
      handleTestError(error, title);
    } finally {
      setLoading(false);
    }
  }, [title, inputs, values, onTest, onSuccess, logParams, logSuccess, validateInputs]);

  return (
    <div className="test-wrapper">
      <h4 className="test-wrapper-title">{title}</h4>

      {description && <p className="test-wrapper-description">{description}</p>}

      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 渲染输入框 */}
        {inputs.map((input) => (
          <div key={input.name} className="test-wrapper-input-group">
            <label htmlFor={input.name} className="test-wrapper-label">
              {input.label}
              {input.required ? ' (必填)' : ' (可选)'}:
            </label>
            {input.multiline ? (
              <Input.TextArea
                id={input.name}
                placeholder={input.placeholder || `请输入${input.label}`}
                value={values[input.name] || ''}
                onChange={(e) => handleInputChange(input.name, e.target.value)}
                rows={input.rows || 4}
                style={{ marginTop: 8 }}
              />
            ) : (
              <Input
                id={input.name}
                placeholder={input.placeholder || `请输入${input.label}`}
                value={values[input.name] || ''}
                onChange={(e) => handleInputChange(input.name, e.target.value)}
                type={input.type || 'text'}
                style={{ marginTop: 8 }}
              />
            )}
          </div>
        ))}

        {/* 执行按钮 */}
        <Button
          type={buttonType}
          danger={buttonDanger}
          onClick={handleTest}
          loading={loading}
          block
        >
          {buttonText}
        </Button>

        {/* 自定义结果渲染 */}
        {result && renderResult && (
          <div className="test-wrapper-result">{renderResult(result)}</div>
        )}
      </Space>
    </div>
  );
}

export default TestWrapper;
