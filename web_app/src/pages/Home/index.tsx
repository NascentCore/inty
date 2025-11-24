/**
 * Home 首页 - AI 角色推荐列表
 * 展示推荐的 AI 角色卡片
 */

import { history, useModel } from '@umijs/max';
import React, { useEffect, useRef } from 'react';
import { EmptyState, ErrorAlert, Loading } from '@/components';
import { useInfiniteScroll } from '@/hooks';
import type { IAgent } from '@/types';
import { CharacterCard } from './components';
import './index.less';

/**
 * 首页
 */
const HomePage: React.FC = () => {
  // 获取 agent model
  const { recommendList, loading, error, pagination, loadRecommendAgents, loadMoreRecommendAgents } = useModel('agent');
  
  // 用于存储滚动容器的 ref
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  /**
   * 页面加载时获取推荐角色列表（第一页，每页20条）
   */
  useEffect(() => {
    loadRecommendAgents({ page: 1, page_size: 20 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 仅在页面首次加载时执行

  /**
   * 使用无限滚动 hook，实现滚动到底部自动加载
   */
  useInfiniteScroll({
    containerRef: scrollContainerRef,
    loading,
    pagination,
    loadMore: loadMoreRecommendAgents,
    threshold: 200,
  });

  /**
   * 处理开始对话
   */
  const handleStartChat = (agent: IAgent) => {
    history.push(`/chat/${agent.id}`);
  };

  /**
   * 处理下载按钮点击
   */
  const handleDownloadClick = () => {
    window.open('https://play.google.com/store/apps/details?id=com.ai.intellimate', '_blank');
  };

  return (
    <div className="home-page" ref={scrollContainerRef}>
      {/* 页面标题 */}
      <div className="page-header">
        <h1 className="page-title">discover</h1>
        <button type="button" className="download-button" onClick={handleDownloadClick}>
          <img
            src="https://upload.wikimedia.org/wikipedia/commons/7/78/Google_Play_Store_badge_EN.svg"
            alt="Get it on Google Play"
            loading="lazy"
          />
        </button>
      </div>

      <div className="page-content">
        {/* 错误提示 */}
        {error && <ErrorAlert message="Failed to load" description={error} type="error" closable />}

        {/* 初始加载状态 */}
        {loading && recommendList.length === 0 && <Loading tip="Loading..." size="large" fullscreen />}

        {/* 角色卡片列表 */}
        {recommendList.length > 0 && (
          <div className="character-grid">
            {recommendList.map((agent: IAgent) => (
              <CharacterCard key={agent.id} agent={agent} onStartChat={handleStartChat} />
            ))}
          </div>
        )}

        {/* 加载更多指示器 */}
        {loading && recommendList.length > 0 && (
          <div className="loading-more">
            <Loading tip="Loading more..." size="small" />
          </div>
        )}

        {/* 空状态 */}
        {!loading && !error && recommendList.length === 0 && (
          <EmptyState description="No recommended agents" />
        )}

        {/* 没有更多数据提示 */}
        {!loading && recommendList.length > 0 && pagination.page >= pagination.totalPages && (
          <div className="no-more-data">No more agents</div>
        )}
      </div>
    </div>
  );
};

export default HomePage;
