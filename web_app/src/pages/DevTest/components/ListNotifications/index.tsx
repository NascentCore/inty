import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取通知列表测试组件
 */
const ListNotifications: React.FC = () => {
  return (
    <TestWrapper
      title="获取通知列表"
      description="分页查询用户的通知消息列表"
      inputs={[
        {
          name: 'is_read',
          label: '是否已读',
          required: false,
          type: 'select',
          options: [
            { label: '全部', value: undefined },
            { label: '未读', value: false },
            { label: '已读', value: true },
          ],
        },
        {
          name: 'page',
          label: '页码',
          required: false,
          type: 'number',
          defaultValue: 1,
        },
        {
          name: 'page_size',
          label: '每页数量',
          required: false,
          type: 'number',
          defaultValue: 20,
        },
      ]}
      onTest={async (values) => {
        const params: any = {
          page: values.page || 1,
          page_size: values.page_size || 20,
        };

        if (values.is_read !== undefined) {
          params.is_read = values.is_read;
        }

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.listNotifications(params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('通知总数', response.data.total);
          logger.testDetail('当前页', response.data.page);
          logger.testDetail('总页数', response.data.total_pages);
          response.data.items?.slice(0, 5).forEach((item: any, index: number) => {
            logger.testDetail(`通知 ${index + 1}`, {
              title: item.title,
              is_read: item.is_read,
              created_at: item.created_at,
            });
          });
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default ListNotifications;

