/**
 * Home 首页 - AI 角色推荐列表
 * 展示推荐的 AI 角色卡片
 */

import { history, useModel } from '@umijs/max';
import React, { useEffect } from 'react';
import { EmptyState, ErrorAlert, Loading } from '@/components';
import type { IAgent } from '@/types';
import { CharacterCard } from './components';
import './index.less';

/**
 * 首页
 */
const HomePage: React.FC = () => {
  // 获取 agent model
  const { recommendList, loading, error, loadRecommendAgents } = useModel('agent');

  /**
   * 页面加载时获取推荐角色列表
   */
  useEffect(() => {
    loadRecommendAgents({ page: 1, page_size: 100 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 仅在页面首次加载时执行

  /**
   * 处理开始对话
   */
  const handleStartChat = (agent: IAgent) => {
    history.push(`/chat/${agent.id}`);
  };

  return (
    <div className="home-page">
      {/* 页面标题 */}
      <div className="page-header">
        <h1 className="page-title">discover</h1>
      </div>

      {/* 错误提示 */}
      {error && <ErrorAlert message="Failed to load" description={error} type="error" closable />}

      {/* 加载状态 */}
      {loading && <Loading tip="Loading..." size="large" fullscreen />}

      {/* 角色卡片列表 */}
      {!loading && recommendList.length > 0 && (
        <div className="character-grid">
          {recommendList.map((agent: IAgent) => (
            <CharacterCard key={agent.id} agent={agent} onStartChat={handleStartChat} />
          ))}
        </div>
      )}

      {/* 空状态 */}
      {!loading && !error && recommendList.length === 0 && (
        <EmptyState description="No recommended agents" />
      )}
    </div>
  );
};

export default HomePage;
