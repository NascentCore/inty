import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 验证购买测试组件
 */
const VerifyPurchase: React.FC = () => {
  return (
    <TestWrapper
      title="验证购买"
      description="验证 Google Play 或 App Store 的购买"
      inputs={[
        {
          name: 'product_id',
          label: 'Product ID',
          required: true,
          placeholder: '请输入 Product ID',
        },
        {
          name: 'purchase_token',
          label: 'Purchase Token',
          required: true,
          placeholder: '请输入 Purchase Token',
        },
        {
          name: 'order_id',
          label: 'Order ID',
          required: false,
          placeholder: '请输入 Order ID（可选）',
        },
      ]}
      onTest={async (values) => {
        const params: any = {
          product_id: values.product_id,
          purchase_token: values.purchase_token,
        };
        if (values.order_id) {
          params.order_id = values.order_id;
        }

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.subscription.verify(params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('验证结果', response.data.is_verified);
          logger.testDetail('消息', response.data.message);
          logger.testDetail('订阅信息', response.data.subscription);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default VerifyPurchase;

