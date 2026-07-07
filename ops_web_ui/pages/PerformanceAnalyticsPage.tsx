import React from "react";
import { PerformanceAnalyticsSection } from "../components/userAnalytics/PerformanceAnalyticsSection";

/**
 * 性能监控页面
 * 由用户日报周报中的复用组件构成，避免两处实现分叉
 */
export const PerformanceAnalyticsPage: React.FC = () => (
  <div style={{ padding: "24px" }}>
    <PerformanceAnalyticsSection />
  </div>
);
