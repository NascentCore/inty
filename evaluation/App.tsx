/**
 * 评测系统主应用组件
 * 包含路由管理、导航菜单、全局状态管理
 */

import React, { useState, useEffect } from "react";
import { Layout, Menu, Typography, Tooltip, Button, Spin } from "antd";
import {
  RobotOutlined,
  MessageOutlined,
  BarChartOutlined,
  HistoryOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SettingOutlined,
  UserOutlined,
  AppstoreOutlined,
  PictureOutlined,
  ExclamationCircleOutlined,
  PhoneOutlined,
  FileTextOutlined,
  CalendarOutlined,
  CalculatorOutlined,
} from "@ant-design/icons";
import { EvaluationPage } from "./pages/EvaluationPage";
import { EvaluationHistoryPage } from "./pages/EvaluationHistoryPage";
import { ChatPage } from "./pages/ChatPage";
import { ChatWsVerifyPage } from "./pages/ChatWsVerifyPage";
import AgentManagePage from "./pages/AgentManagePage";
import CharacterThemeManagePage from "./pages/CharacterThemeManagePage";
import { SettingsPage } from "./pages/SettingsPage";
import { UserAnalyticsPage } from "./pages/UserAnalyticsPage";
import { UserAnalyticsReportsPage } from "./pages/UserAnalyticsReportsPage";
import { UserDailyMessagesPage } from "./pages/UserDailyMessagesPage";
import GeneratedImagesPage from "./pages/GeneratedImagesPage";
import { ReportFeedbackPage } from "./pages/ReportFeedbackPage";
import { ReportUserConversationsPage } from "./pages/ReportUserConversationsPage";
import { VoiceChatPage } from "./pages/VoiceChatPage";
import { VoiceRecordingPage } from "./pages/VoiceRecordingPage";
import { FestivalMemoryPage } from "./pages/FestivalMemoryPage";
import { LlmMonthlyBillingPage } from "./pages/LlmMonthlyBillingPage";
import { ApiKeyProvider, useApiKeyContext } from "./hooks/useApiKey";
import { ApiKeyModal } from "./components/ApiKeyModal";
import { UserInfo } from "./components/UserInfo";
import { AssumeUserSelector } from "./components/AssumeUserSelector";
import { parseEvaluationHashRoute } from "./utils/profileLinks";

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

/** Height reserved for the sidebar header (logo + hamburger), used for scroll area max-height. */
const SIDER_HEADER_HEIGHT_PX = 80;
/** Minimum height of each sidebar menu row (icon + label area). */
const MENU_ROW_MIN_HEIGHT_PX = 40;

type PageKey =
  | "evaluation"
  | "history"
  | "chat"
  | "chat-ws-verify"
  | "voice-chat"
  | "agents"
  | "settings"
  | "user-analytics"
  | "user-analytics-reports"
  | "user-daily-messages"
  | "character-themes"
  | "generated-images"
  | "report-feedback"
  | "report-user-conversations"
  | "festival-memory"
  | "llm-monthly-billing"
  | "voice-recording";

const HASH_PAGE_KEYS = new Set<PageKey>([
  "evaluation",
  "history",
  "chat",
  "chat-ws-verify",
  "voice-chat",
  "agents",
  "settings",
  "user-analytics",
  "user-analytics-reports",
  "user-daily-messages",
  "character-themes",
  "generated-images",
  "report-feedback",
  "report-user-conversations",
  "festival-memory",
  "llm-monthly-billing",
  "voice-recording",
]);

interface NavigationItem {
  key: PageKey;
  icon: React.ReactNode;
  label: string;
  description: string;
}

// 主应用内容组件
const AppContent: React.FC = () => {
  // 状态管理
  const [currentPage, setCurrentPage] = useState<PageKey>(() => {
    if (typeof window !== "undefined") {
      const { pageKey } = parseEvaluationHashRoute(window.location.hash);
      if (HASH_PAGE_KEYS.has(pageKey as PageKey)) {
        return pageKey as PageKey;
      }
    }
    const savedPage = localStorage.getItem("lastVisitedPage");
    if (savedPage === "live2d") {
      return "chat";
    }
    if (savedPage === "performance-analytics") {
      return "user-analytics-reports";
    }
    return (savedPage as PageKey) || "chat";
  });
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);

  // API Key 管理
  const { isApiKeyValid, isLoading } = useApiKeyContext();

  // GEMINI: 将当前页面保存到 localStorage
  useEffect(() => {
    localStorage.setItem("lastVisitedPage", currentPage);
  }, [currentPage]);

  useEffect(() => {
    const onHashChange = () => {
      const { pageKey } = parseEvaluationHashRoute(window.location.hash);
      if (HASH_PAGE_KEYS.has(pageKey as PageKey)) {
        setCurrentPage(pageKey as PageKey);
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // 响应式检测
  useEffect(() => {
    const checkScreenSize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile && !collapsed) {
        setCollapsed(true);
      }
    };

    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);

    return () => {
      window.removeEventListener("resize", checkScreenSize);
    };
  }, [collapsed]);

  // 应用加载完成后隐藏加载动画
  useEffect(() => {
    // 延迟一小段时间确保应用完全加载
    const timer = setTimeout(() => {
      if (typeof window !== "undefined" && window.hideLoading) {
        window.hideLoading();
        console.log("应用加载完成，隐藏加载动画");
      }
    }, 500);

    return () => clearTimeout(timer);
  }, []);

  // 检查是否需要显示 API Key 模态框
  useEffect(() => {
    if (!isLoading && !isApiKeyValid) {
      setShowApiKeyModal(true);
    }
  }, [isLoading, isApiKeyValid]);

  // 如果正在加载，显示加载状态
  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <Spin size="large" />
        <Text type="secondary">正在验证 API Key...</Text>
      </div>
    );
  }

  // 处理侧边栏折叠/展开
  const handleCollapse = (collapsed: boolean) => {
    setCollapsed(collapsed);
  };

  // 导航菜单配置
  const navigationItems: NavigationItem[] = [
    {
      key: "user-analytics-reports",
      icon: <FileTextOutlined />,
      label: "用户日报周报",
      description: "全部用户预计算日报与周报",
    },
    {
      key: "report-feedback",
      icon: <ExclamationCircleOutlined />,
      label: "举报与反馈",
      description: "查看用户举报和反馈列表",
    },
    {
      key: "agents",
      icon: <RobotOutlined />,
      label: "智能体管理",
      description: "创建、编辑和管理智能体",
    },
    {
      key: "chat",
      icon: <MessageOutlined />,
      label: "单角色聊天",
      description: "与智能体进行一对一聊天",
    },
    {
      key: "chat-ws-verify",
      icon: <MessageOutlined />,
      label: "WebSocket 对话验证",
      description: "走生产 /api/v1/chat/ws，与线上一致（Assume user 走 query）",
    },
    {
      key: "voice-chat",
      icon: <PhoneOutlined />,
      label: "语音通话",
      description: "与智能体进行实时语音对话",
    },
    {
      key: "character-themes",
      icon: <AppstoreOutlined />,
      label: "角色专区管理",
      description: "创建和管理角色主题专区",
    },
    {
      key: "evaluation",
      icon: <BarChartOutlined />,
      label: "智能体评测",
      description: "创建和管理智能体评测任务",
    },
    {
      key: "history",
      icon: <HistoryOutlined />,
      label: "评测记录",
      description: "查看历史评测会话和结果",
    },
    {
      key: "user-analytics",
      icon: <UserOutlined />,
      label: "用户数据分析",
      description: "查看用户注册和聊天行为数据",
    },
    {
      key: "user-daily-messages",
      icon: <MessageOutlined />,
      label: "用户每日消息",
      description: "查询用户每日聊天记录和会话历史",
    },
    {
      key: "generated-images",
      icon: <PictureOutlined />,
      label: "生成图片管理",
      description: "查看角色聊天生成的所有图片",
    },
    {
      key: "festival-memory",
      icon: <CalendarOutlined />,
      label: "节日记忆提取",
      description: "配置节日与提示词，抽取用户与角色的节日回忆",
    },
    {
      key: "llm-monthly-billing",
      icon: <CalculatorOutlined />,
      label: "模型月度账单",
      description: "按模型定价与用量计算月度费用",
    },
    {
      key: "settings",
      icon: <SettingOutlined />,
      label: "消息生图系统设置",
      description: "配置图片生成等系统参数",
    },
  ];

  // 获取页面标题
  const getPageTitle = () => {
    switch (currentPage) {
      case "evaluation":
        return "智能体评测";
      case "history":
        return "智能体评测记录";
      case "chat":
        return "单角色聊天";
      case "chat-ws-verify":
        return "WebSocket 对话验证";
      case "voice-chat":
        return "语音通话";
      case "agents":
        return "智能体管理";
      case "character-themes":
        return "角色专区管理";
      case "settings":
        return "消息生图系统设置";
      case "user-analytics":
        return "用户数据分析";
      case "user-analytics-reports":
        return "用户日报周报";
      case "user-daily-messages":
        return "用户每日消息";
      case "generated-images":
        return "生成图片管理";
      case "report-feedback":
        return "举报与反馈";
      case "report-user-conversations":
        return "举报用户聊天记录";
      case "festival-memory":
        return "节日记忆提取";
      case "llm-monthly-billing":
        return "模型月度账单计算器";
      case "voice-recording":
        return "语音通话录音";
      default:
        return "智能体评测系统";
    }
  };

  // 渲染页面内容
  const renderPageContent = () => {
    switch (currentPage) {
      case "evaluation":
        return <EvaluationPage />;
      case "history":
        return (
          <EvaluationHistoryPage
            onNavigateToEvaluation={() => setCurrentPage("evaluation")}
          />
        );
      case "chat":
        return <ChatPage />;
      case "chat-ws-verify":
        return <ChatWsVerifyPage />;
      case "voice-chat":
        return (
          <VoiceChatPage
            onNavigateToUserDailyMessages={() =>
              setCurrentPage("user-daily-messages")
            }
          />
        );
      case "agents":
        return <AgentManagePage />;
      case "character-themes":
        return <CharacterThemeManagePage />;
      case "settings":
        return <SettingsPage />;
      case "user-analytics":
        return <UserAnalyticsPage />;
      case "user-analytics-reports":
        return <UserAnalyticsReportsPage />;
      case "user-daily-messages":
        return <UserDailyMessagesPage />;
      case "generated-images":
        return <GeneratedImagesPage />;
      case "report-feedback":
        return (
          <ReportFeedbackPage
            onNavigateToReportUserConversations={(reportId) => {
              setCurrentPage("report-user-conversations");
              if (typeof window !== "undefined") {
                const base = `${window.location.origin}${window.location.pathname}`;
                window.history.replaceState(
                  null,
                  "",
                  `${base}#report-user-conversations?reportId=${encodeURIComponent(reportId)}`,
                );
              }
            }}
          />
        );
      case "report-user-conversations":
        return (
          <ReportUserConversationsPage
            onBack={() => {
              setCurrentPage("report-feedback");
              if (typeof window !== "undefined") {
                const hash = window.location.hash;
                const params = new URLSearchParams(hash.split("?")[1] || "");
                const reportId = params.get("reportId");
                const base = `${window.location.origin}${window.location.pathname}`;
                const nextHash = reportId
                  ? `#report-feedback?reportId=${encodeURIComponent(reportId)}`
                  : "#report-feedback";
                window.history.replaceState(null, "", `${base}${nextHash}`);
              }
            }}
          />
        );
      case "festival-memory":
        return <FestivalMemoryPage />;
      case "llm-monthly-billing":
        return <LlmMonthlyBillingPage />;
      case "voice-recording":
        return <VoiceRecordingPage />;

      default:
        return null;
    }
  };

  return (
    <>
      <Layout style={{ minHeight: "100vh" }}>
        {/* 侧边导航 */}
        <Sider
          collapsible={false}
          collapsed={collapsed}
          width={220}
          collapsedWidth={80}
          style={{
            overflow: "hidden",
            height: "100vh",
            position: "fixed",
            left: 0,
            top: 0,
            bottom: 0,
            zIndex: 100,
            boxShadow: "2px 0 8px 0 rgba(29, 35, 41, 0.05)",
            display: "flex",
            flexDirection: "column",
          }}
          theme="light"
          breakpoint="lg"
          onBreakpoint={(broken) => {
            if (broken) {
              setCollapsed(true);
            }
          }}
        >
          <div
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            {/* Logo区域 - 添加汉堡按钮 */}
            <div
              style={{
                padding: collapsed ? "16px 12px" : "16px 24px",
                borderBottom: "1px solid #f0f0f0",
                display: "flex",
                alignItems: "center",
                justifyContent: collapsed ? "center" : "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center" }}>
                {collapsed ? (
                  /* 收起状态：显示汉堡按钮 */
                  <Button
                    type="text"
                    icon={<MenuUnfoldOutlined />}
                    onClick={() => handleCollapse(false)}
                    style={{
                      padding: "4px 8px",
                      height: "32px",
                      width: "32px",
                      borderRadius: "6px",
                      color: "#1890ff",
                      border: "1px solid #d9d9d9",
                      fontSize: "16px",
                    }}
                    title="展开菜单"
                  />
                ) : (
                  /* 展开状态：显示标题 */
                  <Title level={4} style={{ margin: 0, color: "#1890ff" }}>
                    InTy 评测
                  </Title>
                )}
              </div>

              {/* 汉堡按钮 - 仅在展开状态显示 */}
              {!collapsed && (
                <Button
                  type="text"
                  icon={<MenuFoldOutlined />}
                  onClick={() => handleCollapse(true)}
                  style={{
                    padding: "4px 8px",
                    height: "32px",
                    width: "32px",
                    borderRadius: "6px",
                    color: "#666",
                    border: "1px solid #d9d9d9",
                  }}
                  title="收起菜单"
                />
              )}
            </div>

            {/* 导航菜单容器 */}
            <div
              style={{
                flex: 1,
                minHeight: 0,
                maxHeight: `calc(100vh - ${SIDER_HEADER_HEIGHT_PX}px)`,
                overflowY: "auto",
                overflowX: "hidden",
                paddingBottom: collapsed ? "20px" : "80px", // 为底部预留空间
              }}
            >
              <Menu
                mode="inline"
                selectedKeys={[currentPage]}
                style={{
                  border: "none",
                  paddingTop: "16px",
                  background: "transparent",
                }}
                items={navigationItems.map((item) => ({
                  key: item.key,
                  icon: undefined,
                  label: (
                    <Tooltip
                      title={collapsed ? item.label : ""}
                      placement="right"
                      overlayClassName="collapsed-menu-tooltip"
                      color="#ffffff"
                    >
                      <div
                        style={{
                          flex: 1,
                          minHeight: `${MENU_ROW_MIN_HEIGHT_PX}px`,
                          display: "flex",
                          flexDirection: collapsed ? "row" : "column",
                          alignItems: collapsed ? "center" : "flex-start",
                          justifyContent: collapsed ? "center" : "flex-start",
                          width: "100%",
                        }}
                      >
                        <span
                          style={{
                            flexShrink: 0,
                            display: "inline-flex",
                            marginRight: collapsed ? 0 : 8,
                          }}
                        >
                          {item.icon}
                        </span>
                        {!collapsed && (
                          <>
                            <div
                              style={{
                                fontSize: "14px",
                                fontWeight: "500",
                                lineHeight: "1.4",
                                color: "rgba(0, 0, 0, 0.85)",
                                marginBottom: "2px",
                              }}
                            >
                              {item.label}
                            </div>
                            <div
                              style={{
                                fontSize: "11px",
                                lineHeight: "1.3",
                                color: "rgba(0, 0, 0, 0.45)",
                                marginTop: "2px",
                              }}
                            >
                              {item.description}
                            </div>
                          </>
                        )}
                      </div>
                    </Tooltip>
                  ),
                  onClick: () => setCurrentPage(item.key),
                  style: {
                    height: "auto",
                    lineHeight: "normal",
                    padding: collapsed ? "12px" : "12px 24px",
                    marginBottom: "4px",
                    borderRadius: "6px",
                    display: "flex",
                    alignItems: "flex-start",
                  },
                }))}
              />
            </div>

            {/* 底部区域 */}
            <div
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                background: "inherit",
              }}
            ></div>
          </div>
        </Sider>

        {/* 主内容区域 */}
        <Layout
          style={{
            marginLeft: isMobile ? 0 : collapsed ? 80 : 220,
            transition: "margin-left 0.2s",
            minHeight: "100vh",
          }}
        >
          {/* 页面头部 */}
          <div
            style={{
              background: "#fff",
              padding: "16px 24px",
              borderBottom: "1px solid #f0f0f0",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <Title level={4} style={{ margin: 0 }}>
                {getPageTitle()}
              </Title>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <AssumeUserSelector />
              <UserInfo onShowApiKeyModal={() => setShowApiKeyModal(true)} />
            </div>
          </div>

          {/* 页面内容 */}
          <Content
            style={{
              background: "#f0f2f5",
              minHeight: "calc(100vh - 73px)",
              overflow: "auto",
              position: "relative",
            }}
          >
            {renderPageContent()}
          </Content>
        </Layout>
      </Layout>

      {/* API Key 模态框 */}
      <ApiKeyModal
        visible={showApiKeyModal}
        onClose={() => setShowApiKeyModal(false)}
        allowClose={isApiKeyValid}
      />
    </>
  );
};

// 主应用组件，包装 API Key Provider
export const App: React.FC = () => {
  return (
    <ApiKeyProvider>
      <AppContent />
    </ApiKeyProvider>
  );
};
