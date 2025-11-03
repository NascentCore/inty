import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取语音列表测试组件
 */
const ListVoices: React.FC = () => {
  return (
    <TestWrapper
      title="获取语音列表"
      description="获取 ElevenLabs 可用的音色列表"
      inputs={[
        {
          name: 'search',
          label: '搜索关键词',
          required: false,
          placeholder: '搜索音色名称',
        },
        {
          name: 'category',
          label: '音色分类',
          required: false,
          placeholder: 'premade / cloned',
        },
        {
          name: 'voice_type',
          label: '音色类型',
          required: false,
          placeholder: 'personal / community',
        },
        {
          name: 'page_size',
          label: '返回数量',
          required: false,
          type: 'number',
          placeholder: '最大 1000',
        },
      ]}
      onTest={async (values) => {
        // 过滤空值
        const params: any = {};
        if (values.search) params.search = values.search;
        if (values.category) params.category = values.category;
        if (values.voice_type) params.voice_type = values.voice_type;
        if (values.page_size) params.page_size = values.page_size;

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.textToSpeech.listVoices(params);

        // 自定义成功日志
        if (response) {
          logger.testDetail('语音数量', response.length);
          response.slice(0, 5).forEach((voice: any, index: number) => {
            logger.testDetail(`语音 ${index + 1}`, {
              id: voice.id,
              name: voice.name,
              language: voice.language,
            });
          });
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default ListVoices;

