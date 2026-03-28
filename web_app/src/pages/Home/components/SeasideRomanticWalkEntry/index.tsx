/**
 * SeasideRomanticWalkEntry 组件
 *
 * 用途：在首页展示「Seaside Romantic Evening Walk」场景入口
 * 使用示例：
 * ```tsx
 * <SeasideRomanticWalkEntry onExplore={handleExploreSeasideWalk} />
 * ```
 *
 * Props 说明：
 * - onExplore: () => void - 点击入口后的跳转动作
 *
 * 注意事项：
 * - 该组件只负责展示和触发行为，不处理路由逻辑
 */
import React from 'react';
import './index.less';

interface ISeasideRomanticWalkEntryProps {
  /** 点击 Explore 按钮回调 */
  onExplore: () => void;
}

const SeasideRomanticWalkEntry: React.FC<ISeasideRomanticWalkEntryProps> = ({ onExplore }) => {
  return (
    <section className="seaside-romantic-walk-entry">
      <div className="seaside-romantic-walk-entry__overlay" />
      <div className="seaside-romantic-walk-entry__content">
        <span className="seaside-romantic-walk-entry__badge">NEW SCENARIO</span>
        <h2 className="seaside-romantic-walk-entry__title">Seaside Romantic Evening Walk</h2>
        <p className="seaside-romantic-walk-entry__description">
          Slow down, walk beside the waves at sunset, and enjoy a calm, intimate conversation mood.
        </p>
        <button
          className="seaside-romantic-walk-entry__button"
          type="button"
          onClick={onExplore}
          aria-label="Explore seaside romantic evening walk"
        >
          Explore this scene
        </button>
      </div>
    </section>
  );
};

export default SeasideRomanticWalkEntry;
