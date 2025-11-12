/**
 * PlanCard 订阅计划卡片组件
 *
 * 用途：展示单个订阅计划的详细信息，包括价格、功能列表等
 * 使用示例：
 * ```tsx
 * <PlanCard
 *   plan={plan}
 *   isCurrentPlan={false}
 *   isRecommended={true}
 *   onSelect={handleSelect}
 * />
 * ```
 *
 * Props 说明：
 * - plan: ISubscriptionPlan - 订阅计划数据
 * - isCurrentPlan: boolean - 是否为当前订阅计划
 * - isRecommended: boolean - 是否为推荐计划（通常是季度计划）
 * - onSelect: (plan: ISubscriptionPlan) => void - 选择计划的回调函数
 *
 * 注意事项：
 * - 折扣率小于1时会显示折扣标签
 * - 当前订阅计划会显示特殊样式
 * - 推荐计划会显示推荐标签
 */

import { Check } from 'lucide-react';
import React from 'react';
import Icon from '@/components/Icon';
import type { ISubscriptionPlan } from '@/types';
import './index.less';

interface IPlanCardProps {
  /** 订阅计划数据 */
  plan: ISubscriptionPlan;
  /** 是否为当前订阅计划 */
  isCurrentPlan?: boolean;
  /** 是否为推荐计划 */
  isRecommended?: boolean;
  /** 选择计划的回调 */
  onSelect?: (plan: ISubscriptionPlan) => void;
}

const PlanCard: React.FC<IPlanCardProps> = ({
  plan,
  isCurrentPlan = false,
  isRecommended = false,
  onSelect,
}) => {
  // 计算折扣百分比
  const discountPercent = plan.discount_rate < 1 ? Math.round((1 - plan.discount_rate) * 100) : 0;

  // 获取计划类型显示文本
  const getPlanTypeText = (type: string): string => {
    const typeMap: Record<string, string> = {
      MONTHLY: 'Monthly Plan',
      QUARTERLY: 'Quarterly Plan',
      YEARLY: 'Annual Plan',
    };
    return typeMap[type] || type;
  };

  // 处理选择按钮点击
  const handleSelect = (): void => {
    if (!isCurrentPlan && onSelect) {
      onSelect(plan);
    }
  };

  return (
    <div
      className={`plan-card ${isCurrentPlan ? 'plan-card-current' : ''} ${
        isRecommended ? 'plan-card-recommended' : ''
      }`}
    >
      {/* 推荐标签 */}
      {isRecommended && !isCurrentPlan && <div className="plan-card-badge">Most Popular</div>}

      {/* 折扣标签 */}
      {discountPercent > 0 && <div className="plan-card-discount">Save {discountPercent}%</div>}

      {/* 计划头部 */}
      <div className="plan-card-header">
        <h3 className="plan-card-title">{plan.name}</h3>
        <p className="plan-card-type">{getPlanTypeText(plan.plan_type)}</p>
      </div>

      {/* 价格区域 */}
      <div className="plan-card-price">
        <span className="plan-card-price-currency">{plan.currency}</span>
        <span className="plan-card-price-amount">{plan.price.toFixed(2)}</span>
        <span className="plan-card-price-period">
          /
          {plan.plan_type === 'MONTHLY'
            ? 'month'
            : plan.plan_type === 'QUARTERLY'
              ? 'quarter'
              : 'year'}
        </span>
      </div>

      {/* 计划描述 */}
      {plan.description && <p className="plan-card-description">{plan.description}</p>}

      {/* 功能列表 */}
      <div className="plan-card-features">
        {plan.features.features
          .sort((a, b) => a.order - b.order)
          .map((feature) => (
            <div key={feature.key} className="plan-card-feature">
              <Icon
                icon={Check}
                size={16}
                color="rgba(82, 196, 26, 1)"
                className="plan-card-feature-icon"
              />
              <div className="plan-card-feature-content">
                <span className="plan-card-feature-icon-emoji">{feature.icon}</span>
                <span className="plan-card-feature-name">{feature.name}</span>
              </div>
            </div>
          ))}
      </div>

      {/* 选择按钮 */}
      <button
        className={`plan-card-button ${isCurrentPlan ? 'plan-card-button-current' : ''}`}
        onClick={handleSelect}
        disabled={isCurrentPlan}
      >
        {isCurrentPlan ? 'Current Plan' : 'Select Plan'}
      </button>
    </div>
  );
};

export default PlanCard;
