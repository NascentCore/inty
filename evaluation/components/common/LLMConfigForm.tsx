import React from "react";
import { Form, Radio, Row, Col, Input, Divider } from "antd";
import ModelSelector from "./ModelSelector";
import type { OpenRouterModel } from "../../types";

interface LLMConfigFormProps {
    models: OpenRouterModel[];
    loading?: boolean;
    onRefresh?: () => void;
    showModelType?: boolean;
    showAdvancedParams?: boolean;
    disabled?: boolean;
}

export const LLMConfigForm: React.FC<LLMConfigFormProps> = ({
    models,
    loading = false,
    onRefresh,
    showModelType = true,
    showAdvancedParams = true,
    disabled = false,
}) => {
    return (
        <>
            {showModelType && (
                <>
                    <Divider>模型配置</Divider>
                    <Form.Item
                        name="modelType"
                        label="模型类型"
                        initialValue="default"
                        rules={[{ required: true, message: "请选择模型类型" }]}
                    >
                        <Radio.Group disabled={disabled}>
                            <Radio value="default">使用默认模型</Radio>
                            <Radio value="custom">自定义模型</Radio>
                        </Radio.Group>
                    </Form.Item>
                </>
            )}

            <Form.Item
                noStyle
                shouldUpdate={(prevValues, currentValues) =>
                    prevValues.modelType !== currentValues.modelType
                }
            >
                {({ getFieldValue }) =>
                    getFieldValue("modelType") === "custom" && (
                        <>
                            <ModelSelector
                                models={models}
                                loading={loading}
                                onRefresh={onRefresh}
                                disabled={disabled}
                            />

                            {showAdvancedParams && (
                                <>
                                    <Row gutter={16}>
                                        <Col span={12}>
                                            <Form.Item
                                                name="temperature"
                                                label="温度"
                                                initialValue={0.7}
                                                rules={[{ required: true, message: "请输入温度值" }]}
                                            >
                                                <Input
                                                    type="number"
                                                    min={0}
                                                    max={2}
                                                    step={0.1}
                                                    disabled={disabled}
                                                />
                                            </Form.Item>
                                        </Col>
                                        <Col span={12}>
                                            <Form.Item
                                                name="max_tokens"
                                                label="最大令牌数"
                                                initialValue={2048}
                                                rules={[{ required: true, message: "请输入最大令牌数" }]}
                                            >
                                                <Input
                                                    type="number"
                                                    min={1}
                                                    max={8192}
                                                    disabled={disabled}
                                                />
                                            </Form.Item>
                                        </Col>
                                    </Row>

                                    <Row gutter={16}>
                                        <Col span={8}>
                                            <Form.Item
                                                name="top_p"
                                                label="Top P"
                                                initialValue={1}
                                                rules={[{ required: true, message: "请输入Top P值" }]}
                                            >
                                                <Input
                                                    type="number"
                                                    min={0}
                                                    max={1}
                                                    step={0.1}
                                                    disabled={disabled}
                                                />
                                            </Form.Item>
                                        </Col>
                                        <Col span={8}>
                                            <Form.Item
                                                name="frequency_penalty"
                                                label="频率惩罚"
                                                initialValue={0}
                                                rules={[{ required: true, message: "请输入频率惩罚值" }]}
                                            >
                                                <Input
                                                    type="number"
                                                    min={-2}
                                                    max={2}
                                                    step={0.1}
                                                    disabled={disabled}
                                                />
                                            </Form.Item>
                                        </Col>
                                        <Col span={8}>
                                            <Form.Item
                                                name="presence_penalty"
                                                label="存在惩罚"
                                                initialValue={0}
                                                rules={[{ required: true, message: "请输入存在惩罚值" }]}
                                            >
                                                <Input
                                                    type="number"
                                                    min={-2}
                                                    max={2}
                                                    step={0.1}
                                                    disabled={disabled}
                                                />
                                            </Form.Item>
                                        </Col>
                                    </Row>
                                </>
                            )}
                        </>
                    )
                }
            </Form.Item>
        </>
    );
};

export default LLMConfigForm;
