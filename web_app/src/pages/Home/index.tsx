/**
 * Home 首页 - AI 角色推荐列表
 * 展示推荐的 AI 角色卡片
 */

import { history, useModel } from '@umijs/max';
import React, { useEffect, useRef } from 'react';
import { useInfiniteScroll } from '@/hooks';
import type { IAgent } from '@/types';
import { AdHomeTop } from '@/components';
import { CharacterList, SeasideRomanticWalkEntry } from './components';
import './index.less';

/**
 * 首页
 */
const HomePage: React.FC = () => {
  // 获取 agent model
  const { recommendList, loading, pagination, loadRecommendAgents, loadMoreRecommendAgents } =
    useModel('agent');

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
    threshold: 100,
    useWindow: true,
  });

  /**
   * 处理开始对话
   */
  const handleStartChat = (agent: IAgent) => {
    history.push(`/chat/${agent.id}`);
  };

  /**
   * 进入海边浪漫傍晚漫步场景页
   */
  const handleExploreSeasideWalk = (): void => {
    history.push('/seaside-romantic-walk');
  };

  return (
    <div className="home-page" ref={scrollContainerRef}>
      <div className="page-content">
        {/* 首页上方 横向广告 */}
        {/* <AdHomeTop /> */}
        <SeasideRomanticWalkEntry onExplore={handleExploreSeasideWalk} />
        <CharacterList
          recommendList={recommendList}
          loading={loading}
          pagination={pagination}
          onStartChat={handleStartChat}
        />
      </div>
    </div>
  );
};

export default HomePage;
