/**
 * Subscribe 订阅页面
 *
 * 功能：
 * - 展示所有可用的订阅计划
 * - 显示当前订阅状态
 * - 支持选择订阅计划
 * - 显示功能特性对比
 */

import React, { useEffect, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import EmptyState from '@/components/EmptyState';
import ErrorAlert from '@/components/ErrorAlert';
import Icon from '@/components/Icon';
import Loading from '@/components/Loading';
import type { ISubscriptionPlan, ISubscriptionPlansData } from '@/types';
import { createIntyClient } from '@/utils/intyClient';
import { logger } from '@/utils/logger';
import { PlanCard } from './components';
import './index.less';

const Subscribe: React.FC = () => {
  // 状态管理
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [plansData, setPlansData] = useState<ISubscriptionPlansData | null>(null);

  // 获取订阅计划列表
  const fetchPlans = async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const client = await createIntyClient(true);
      const response = await client.api.v1.subscription.listPlans();

      if (response.code === 200 && response.data) {
        setPlansData(response.data);
        logger.info('Successfully fetched subscription plans', {
          planCount: response.data.plans.length,
        });
      } else {
        throw new Error(response.message || 'Failed to fetch subscription plans');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      logger.error('Failed to fetch subscription plans', { error: err });
    } finally {
      setLoading(false);
    }
  };

  // 处理选择计划
  const handleSelectPlan = (plan: ISubscriptionPlan): void => {
    logger.info('Plan selected', { planId: plan.id, planType: plan.plan_type });
    // TODO: 集成支付流程
  };

  // 组件挂载时获取数据
  useEffect(() => {
    fetchPlans();
  }, []);

  // 获取当前订阅计划 ID
  const currentPlanId = plansData?.current_subscription?.plan_id || null;

  // 判断是否为推荐计划（季度计划）
  const isRecommendedPlan = (plan: ISubscriptionPlan): boolean => {
    return plan.plan_type === 'QUARTERLY';
  };

  // 加载状态
  if (loading) {
    return (
      <div className="subscribe-page">
        <Loading />
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="subscribe-page">
        <div className="subscribe-error">
          <ErrorAlert message="Failed to load subscription plans" description={error} type="error" />
          <button className="subscribe-retry-button" onClick={fetchPlans}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  // 空数据状态
  if (!plansData || plansData.plans.length === 0) {
    return (
      <div className="subscribe-page">
        <EmptyState description="No subscription plans available" />
      </div>
    );
  }

  return (
    <div className="subscribe-page">
      {/* 页面头部 */}
      <div className="subscribe-header">
        <h1 className="subscribe-title">Choose Your Plan</h1>
        <p className="subscribe-subtitle">
          Unlock unlimited features and enhance your AI experience
        </p>

        {/* 当前订阅状态提示 */}
        {plansData.current_subscription && (
          <div className="subscribe-current-status">
            <Icon icon={AlertCircle} size={16} color="rgba(24, 144, 255, 1)" />
            <span>
              You are currently subscribed to{' '}
              <strong>
                {plansData.plans.find((p) => p.id === currentPlanId)?.name || 'Premium'}
              </strong>
            </span>
          </div>
        )}

        {/* 曾经订阅提示 */}
        {!plansData.current_subscription && plansData.has_ever_subscribed && (
          <div className="subscribe-previous-status">
            <Icon icon={AlertCircle} size={16} color="rgba(250, 173, 20, 1)" />
            <span>Your previous subscription has expired. Renew to continue enjoying premium features.</span>
          </div>
        )}
      </div>

      {/* 订阅计划列表 */}
      <div className="subscribe-plans">
        {plansData.plans
          .sort((a, b) => a.sort_order - b.sort_order)
          .map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              isCurrentPlan={plan.id === currentPlanId}
              isRecommended={isRecommendedPlan(plan)}
              onSelect={handleSelectPlan}
            />
          ))}
      </div>

      {/* 页面底部说明 */}
      <div className="subscribe-footer">
        <p className="subscribe-footer-note">
          • All plans include unlimited chat messages and premium AI models
        </p>
        <p className="subscribe-footer-note">
          • Subscriptions automatically renew unless canceled
        </p>
        <p className="subscribe-footer-note">
          • Cancel anytime from your account settings
        </p>
      </div>
    </div>
  );
};

export default Subscribe;

