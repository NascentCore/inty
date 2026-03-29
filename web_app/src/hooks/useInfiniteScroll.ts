/**
 * useInfiniteScroll Hook
 * 封装无限滚动加载逻辑
 */

import { useCallback, useEffect, useRef } from 'react';

/**
 * 分页信息接口
 */
interface IPaginationInfo {
  /** 当前页码 */
  page: number;
  /** 总页数 */
  totalPages: number;
}

/**
 * useInfiniteScroll Hook 参数
 */
interface IUseInfiniteScrollParams<T extends HTMLElement = HTMLElement> {
  /** 滚动容器 ref */
  containerRef?: React.RefObject<T | null>;
  /** 是否正在加载 */
  loading: boolean;
  /** 分页信息 */
  pagination: IPaginationInfo;
  /** 加载更多的函数 */
  loadMore: () => Promise<unknown>;
  /** 触发加载的距离阈值（距离底部多少像素时触发），默认 200px */
  threshold?: number;
  /** 是否启用，默认 true */
  enabled?: boolean;
  /** 是否监听窗口滚动，默认 false */
  useWindow?: boolean;
}

/**
 * useInfiniteScroll Hook
 *
 * 用途：实现滚动到底部自动加载更多数据
 * 使用示例：
 * ```tsx
 * const containerRef = useRef<HTMLDivElement>(null);
 * const { loadMoreRecommendAgents, loading, pagination } = useModel('agent');
 *
 * useInfiniteScroll({
 *   containerRef,
 *   loading,
 *   pagination,
 *   loadMore: loadMoreRecommendAgents,
 *   threshold: 200,
 * });
 * ```
 *
 * 功能特性：
 * - 自动监听滚动事件
 * - 距离底部指定距离时触发加载
 * - 防止重复加载
 * - 自动清理事件监听器
 */
export const useInfiniteScroll = <T extends HTMLElement = HTMLElement>({
  containerRef,
  loading,
  pagination,
  loadMore,
  threshold = 200,
  enabled = true,
  useWindow = false,
}: IUseInfiniteScrollParams<T>): void => {
  // 用于防止重复加载的标记
  const isLoadingMoreRef = useRef<boolean>(false);

  /**
   * 处理滚动事件，检测是否滚动到底部
   */
  const handleScroll = useCallback(() => {
    const container = containerRef?.current;
    const docElement = document.documentElement;

    if ((!useWindow && !container) || !enabled || loading || isLoadingMoreRef.current) {
      return;
    }

    // 检查是否还有更多数据
    if (pagination.page >= pagination.totalPages) {
      return;
    }

    // 计算是否接近底部
    const scrollTop = useWindow
      ? window.scrollY || docElement.scrollTop
      : container?.scrollTop || 0;
    const scrollHeight = useWindow ? docElement.scrollHeight : container?.scrollHeight || 0;
    const clientHeight = useWindow ? window.innerHeight : container?.clientHeight || 0;
    const distanceToBottom = scrollHeight - scrollTop - clientHeight;

    if (distanceToBottom < threshold) {
      isLoadingMoreRef.current = true;
      loadMore()
        .finally(() => {
          isLoadingMoreRef.current = false;
        })
        .catch(() => {
          // 错误已在 loadMore 中处理，这里只重置标记
        });
    }
  }, [containerRef, enabled, loading, pagination.page, pagination.totalPages, loadMore, threshold]);

  /**
   * 添加滚动监听
   */
  useEffect(() => {
    const container = containerRef?.current;
    if ((!useWindow && !container) || !enabled) {
      return;
    }

    if (useWindow) {
      window.addEventListener('scroll', handleScroll);
    } else {
      if (!container) {
        return;
      }
      container.addEventListener('scroll', handleScroll);
    }

    return () => {
      if (useWindow) {
        window.removeEventListener('scroll', handleScroll);
      } else {
        container?.removeEventListener('scroll', handleScroll);
      }
    };
  }, [containerRef, handleScroll, enabled, useWindow]);
};
