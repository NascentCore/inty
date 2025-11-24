/**
 * CharacterList 组件
 *
 * 用途：统一展示角色列表及其加载、空状态与结束提示
 * 使用示例：
 * ```tsx
 * <CharacterList
 *   recommendList={recommendList}
 *   loading={loading}
 *   pagination={pagination}
 *   onStartChat={handleStartChat}
 * />
 * ```
 *
 * Props 说明：
 * - recommendList: IAgent[] - 推荐角色列表数据
 * - loading: boolean - 是否处于加载状态
 * - pagination: IAgentModelState['pagination'] - 分页信息
 * - onStartChat: (agent: IAgent) => void - 点击角色开始聊天
 *
 * 注意事项：
 * - 组件内部仅关注展示逻辑，错误提示需在外层处理
 * - 需要保证 onStartChat 回调引用稳定以避免不必要的重渲染
 */

import React from 'react';
import { EmptyState, Loading } from '@/components';
import type { IAgent } from '@/types';
import type { IAgentModelState } from '@/models/agent';
import CharacterCard from '../CharacterCard';
import './index.less';

type IPaginationInfo = IAgentModelState['pagination'];

interface ICharacterListProps {
  /** 推荐角色列表 */
  recommendList: IAgent[];
  /** 是否处于加载状态 */
  loading: boolean;
  /** 分页信息 */
  pagination: IPaginationInfo;
  /** 开始聊天事件 */
  onStartChat: (agent: IAgent) => void;
}

/**
 * CharacterList - 推荐角色列表展示
 */
const CharacterList: React.FC<ICharacterListProps> = ({ recommendList, loading, pagination, onStartChat }) => {
  return (
    <div className="character-list-section">
      {/* 初始加载状态 */}
      {loading && recommendList.length === 0 && <Loading tip="Loading..." size="large" fullscreen />}

      {/* 角色卡片列表 */}
      {recommendList.length > 0 && (
        <div className="character-grid">
          {recommendList.map((agent: IAgent) => (
            <CharacterCard key={agent.id} agent={agent} onStartChat={onStartChat} />
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
      {!loading && recommendList.length === 0 && <EmptyState description="No recommended agents" />}

      {/* 没有更多数据提示 */}
      {!loading && recommendList.length > 0 && pagination.page >= pagination.totalPages && (
        <div className="no-more-data">No more agents</div>
      )}
    </div>
  );
};

export default CharacterList;

