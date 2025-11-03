import React, { useState } from 'react';
import { Select } from 'antd';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取推荐角色列表测试组件
 */
const RecommendAgents: React.FC = () => {
  const [sort, setSort] = useState<string>('score_based_random');

  return (
    <div className="test-component">
      <h4>获取推荐角色列表</h4>

      {/* 排序方式下拉框 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4 }}>排序方式 (可选):</label>
        <Select
          value={sort}
          onChange={setSort}
          style={{ width: '100%' }}
          options={[
            { value: 'score_based_random', label: '基于评分的随机排序' },
            { value: 'random', label: '随机排序' },
            { value: 'created_asc', label: '创建时间升序' },
            { value: 'created_desc', label: '创建时间降序' },
          ]}
        />
      </div>

      <TestWrapper
        title=""
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
            label: '每页数量（最大 100）',
            type: 'number',
            defaultValue: '20',
            placeholder: '20',
          },
          ...(sort === 'random' || sort === 'score_based_random'
            ? [
                {
                  name: 'sort_seed',
                  label: '排序种子（随机排序时使用）',
                  placeholder: '用于确保随机排序的一致性',
                },
              ]
            : []),
        ]}
        onTest={async (values) => {
          const pageNum = Number.parseInt(values.page) || 1;
          const size = Number.parseInt(values.page_size) || 20;

          const params: Record<string, unknown> = {
            page: pageNum,
            page_size: size,
          };

          // 添加排序参数
          if (sort) {
            params.sort = sort;
          }

          // 如果是随机排序，添加种子
          if (
            (sort === 'random' || sort === 'score_based_random') &&
            values.sort_seed
          ) {
            params.sort_seed = values.sort_seed;
          }

          logger.testDetail('请求参数', params);

          const client = await createIntyClient(true);
          const response = await client.api.v1.ai.agents.recommend(params);

          // 自定义成功日志
          if (response.data) {
            logger.testDetail('总数', response.data.total);
            logger.testDetail('当前页', response.data.page);
            logger.testDetail('页大小', response.data.page_size);

            if (response.data.list && response.data.list.length > 0) {
              logger.info(`\n前 3 个角色:`);
              response.data.list.slice(0, 3).forEach((agent: any, index: number) => {
                logger.info(`  ${index + 1}. 名称: ${agent.name}`);
                logger.info(`     ID: ${agent.id}`);
                logger.info(`     性别: ${agent.gender}`);
                logger.info(`     分类: ${agent.category || 'N/A'}`);
                logger.info(
                  `     简介: ${agent.intro?.substring(0, 50) || 'N/A'}...`,
                );
              });
            }
          }

          return response;
        }}
        buttonText="执行测试"
      />
    </div>
  );
};

export default RecommendAgents;

