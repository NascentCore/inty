import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取聊天列表测试组件
 */
const ChatList: React.FC = () => {
  return (
    <TestWrapper
      title="获取聊天列表"
      inputs={[
        {
          name: 'page',
          label: '页码',
          type: 'number',
          defaultValue: '1',
          placeholder: '1',
        },
        {
          name: 'page_size',
          label: '每页数量',
          type: 'number',
          defaultValue: '20',
          placeholder: '20',
        },
      ]}
      onTest={async (values) => {
        const pageNum = Number.parseInt(values.page, 10) || 1;
        const size = Number.parseInt(values.page_size, 10) || 20;
        const skip = (pageNum - 1) * size;
        const limit = size;

        const client = await createIntyClient(true);
        const response = await client.api.v1.chats.list({
          skip,
          limit,
        });

        // 自定义成功日志
        if (Array.isArray(response) && response.length > 0) {
          logger.testDetail('总数', response.length);
          logger.testDetail('当前页', pageNum);
          logger.testDetail('页大小', size);

          logger.info('\n前 3 个会话:');
          response.slice(0, 3).forEach((chat: any, index: number) => {
            logger.info(`  ${index + 1}. Chat ID: ${chat.id}`);
            logger.info(`     Agent ID: ${chat.agent_id}`);
            logger.info(`     创建时间: ${chat.created_at}`);
          });
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default ChatList;
