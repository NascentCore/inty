/**
 * BackToTop 悬浮返回顶部按钮
 *
 * 用途：当页面/容器滚动到一定距离后显示按钮，点击后平滑滚动回顶部。
 * 使用示例：
 * ```tsx
 * const containerRef = useRef<HTMLDivElement>(null);
 *
 * <BackToTop containerRef={containerRef} threshold={400} />
 * ```
 *
 * Props 说明：
 * - containerRef: React.RefObject<HTMLElement | null> - 可选，滚动容器 ref（也会同时监听 window 滚动，保证兼容）
 * - threshold: number - 显示阈值（滚动距离超过该值才显示），默认 400
 * - title: string - aria-label / title 文案，默认 "Back to top"
 *
 * 注意事项：
 * - CREATED_BY_AGENT
 */

import { ArrowUp } from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Icon } from '@/components';
import './index.less';

interface IBackToTopProps {
  /** 滚动容器 ref（可选） */
  containerRef?: React.RefObject<HTMLElement | null>;
  /** 显示阈值 */
  threshold?: number;
  /** aria-label / title 文案 */
  title?: string;
}

const getWindowScrollTop = (): number => {
  return window.scrollY || document.documentElement.scrollTop || 0;
};

/**
 * BackToTop 组件
 */
const BackToTop: React.FC<IBackToTopProps> = ({
  containerRef,
  threshold = 400,
  title = 'Back to top',
}) => {
  const [visible, setVisible] = useState<boolean>(false);

  const getScrollTop = useCallback((): number => {
    const elementScrollTop = containerRef?.current?.scrollTop ?? 0;
    return Math.max(getWindowScrollTop(), elementScrollTop);
  }, [containerRef]);

  const scrollToTop = useCallback(() => {
    // 同时处理 window 与容器，避免实际滚动源与预期不一致导致失效
    containerRef?.current?.scrollTo({ top: 0, behavior: 'smooth' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [containerRef]);

  useEffect(() => {
    const container = containerRef?.current ?? null;

    const handleScroll = () => {
      setVisible(getScrollTop() > threshold);
    };

    // 初始化一次，避免首次渲染状态不一致
    handleScroll();

    window.addEventListener('scroll', handleScroll);
    container?.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      container?.removeEventListener('scroll', handleScroll);
    };
  }, [containerRef, getScrollTop, threshold]);

  const className = useMemo(() => {
    return `back-to-top ${visible ? 'back-to-top--visible' : ''}`;
  }, [visible]);

  return (
    <button
      type="button"
      className={className}
      onClick={scrollToTop}
      aria-label={title}
      title={title}
    >
      <Icon icon={ArrowUp} size={18} />
    </button>
  );
};

export default BackToTop;
