import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取消息历史测试组件
 */
const MessageHistory: React.FC = () => {
  return (
    <TestWrapper
      title="获取消息历史"
      description="注意：SDK 返回所有消息，不支持分页"
      inputs={[
        {
          name: 'agent_id',
          label: 'Agent ID',
          required: true,
          placeholder: '请输入 Agent ID',
        },
      ]}
      onTest={async (values) => {
        const client = await createIntyClient(true);
        const response = await client.api.v1.chats.agents.getMessages(values.agent_id);

        // 自定义成功日志
        if (Array.isArray(response)) {
          logger.info(`总共 ${response.length} 条消息`);

          if (response.length > 0) {
            logger.info('\n前 5 条消息:');
            response.slice(0, 5).forEach((msg: any, index: number) => {
              logger.info(`  ${index + 1}. 角色: ${msg.role}`);
              logger.info(
                `     内容: ${msg.content?.substring(0, 50)}${msg.content?.length > 50 ? '...' : ''}`,
              );
              logger.info(`     时间: ${msg.timestamp || 'N/A'}`);
            });
          }
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default MessageHistory;
