import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Collapse,
  Empty,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from "antd";
import { ArrowLeftOutlined, ReloadOutlined } from "@ant-design/icons";

import { reportApi } from "../services/api";
import type {
  ReportConversationGroupItem,
  ReportConversationMessageItem,
} from "../types";
import { formatUtcTimeRaw } from "../utils/dateUtils";
import {
  getEvaluationBaseUrl,
  parseEvaluationHashRoute,
} from "../utils/profileLinks";

const { Text } = Typography;
const ROUNDS_PER_PAGE = 20;
const MESSAGES_SCROLL_HEIGHT = 420;

type GroupMessagesState = {
  messages: ReportConversationMessageItem[];
  page: number;
  hasMore: boolean;
  totalRounds: number;
  initialized: boolean;
  loading: boolean;
};

function buildGroupKey(group: ReportConversationGroupItem): string {
  return `${group.user_id}:${group.agent_id}`;
}

function isUserMessage(messageType: string): boolean {
  const normalized = messageType.toLowerCase();
  return normalized === "human" || normalized === "user";
}

function getGeneratedImageUrl(
  metaData: ReportConversationMessageItem["meta_data"],
): string | null {
  if (!metaData || typeof metaData !== "object") {
    return null;
  }
  const generatedImage = (
    metaData as { generated_image?: { image_url?: unknown } }
  ).generated_image;
  if (
    generatedImage &&
    typeof generatedImage === "object" &&
    typeof generatedImage.image_url === "string"
  ) {
    return generatedImage.image_url;
  }
  return null;
}

interface ReportUserConversationsPageProps {
  onBack?: () => void;
}

export const ReportUserConversationsPage: React.FC<
  ReportUserConversationsPageProps
> = ({ onBack }) => {
  const [reportId, setReportId] = useState("");
  const [groups, setGroups] = useState<ReportConversationGroupItem[]>([]);
  const [activeGroupKeys, setActiveGroupKeys] = useState<string[]>([]);
  const [loadingGroups, setLoadingGroups] = useState(false);
  const [groupMessages, setGroupMessages] = useState<
    Record<string, GroupMessagesState>
  >({});

  const groupsByKey = useMemo(() => {
    const map: Record<string, ReportConversationGroupItem> = {};
    groups.forEach((group) => {
      map[buildGroupKey(group)] = group;
    });
    return map;
  }, [groups]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const syncReportIdFromHash = () => {
      const parsed = parseEvaluationHashRoute(window.location.hash);
      if (parsed.pageKey !== "report-user-conversations") {
        return;
      }
      setReportId(parsed.params.get("reportId")?.trim() || "");
    };

    syncReportIdFromHash();
    window.addEventListener("hashchange", syncReportIdFromHash);
    return () => window.removeEventListener("hashchange", syncReportIdFromHash);
  }, []);

  const loadGroups = useCallback(async () => {
    if (!reportId) {
      setGroups([]);
      setGroupMessages({});
      setActiveGroupKeys([]);
      return;
    }
    setLoadingGroups(true);
    try {
      const result = await reportApi.getConversationGroups(reportId);
      setGroups(result.items);
      setGroupMessages({});
      setActiveGroupKeys([]);
    } catch (error) {
      console.error("加载举报聊天分组失败:", error);
      message.error("加载聊天分组失败");
    } finally {
      setLoadingGroups(false);
    }
  }, [reportId]);

  useEffect(() => {
    void loadGroups();
  }, [loadGroups]);

  const loadGroupMessages = useCallback(
    async (group: ReportConversationGroupItem, nextPage: number) => {
      const groupKey = buildGroupKey(group);
      setGroupMessages((prev) => ({
        ...prev,
        [groupKey]: {
          messages: prev[groupKey]?.messages || [],
          page: prev[groupKey]?.page || 0,
          hasMore: prev[groupKey]?.hasMore ?? true,
          totalRounds: prev[groupKey]?.totalRounds || 0,
          initialized: true,
          loading: true,
        },
      }));

      try {
        const result = await reportApi.getConversationMessages({
          report_id: reportId,
          user_id: group.user_id,
          agent_id: group.agent_id,
          page: nextPage,
          size: ROUNDS_PER_PAGE,
        });

        setGroupMessages((prev) => {
          const existing = prev[groupKey];
          const mergedMessages =
            nextPage === 1
              ? result.messages
              : [
                  ...(existing?.messages || []),
                  ...result.messages.filter(
                    (messageItem) =>
                      !(existing?.messages || []).some(
                        (existingItem) => existingItem.id === messageItem.id,
                      ),
                  ),
                ];

          return {
            ...prev,
            [groupKey]: {
              messages: mergedMessages,
              page: result.page,
              hasMore: result.has_more,
              totalRounds: result.total_rounds,
              initialized: true,
              loading: false,
            },
          };
        });
      } catch (error) {
        console.error("加载分组聊天消息失败:", error);
        message.error("加载聊天消息失败");
        setGroupMessages((prev) => ({
          ...prev,
          [groupKey]: {
            messages: prev[groupKey]?.messages || [],
            page: prev[groupKey]?.page || 0,
            hasMore: prev[groupKey]?.hasMore ?? true,
            totalRounds: prev[groupKey]?.totalRounds || 0,
            initialized: true,
            loading: false,
          },
        }));
      }
    },
    [reportId],
  );

  const handleCollapseChange = useCallback(
    (keys: string[] | string) => {
      const normalizedKeys = Array.isArray(keys) ? keys : [keys];
      setActiveGroupKeys(normalizedKeys);

      normalizedKeys.forEach((key) => {
        const group = groupsByKey[key];
        if (!group) {
          return;
        }
        if (!groupMessages[key]?.initialized && !groupMessages[key]?.loading) {
          void loadGroupMessages(group, 1);
        }
      });
    },
    [groupMessages, groupsByKey, loadGroupMessages],
  );

  const handleMessagesScroll = useCallback(
    (groupKey: string, event: React.UIEvent<HTMLDivElement>) => {
      const state = groupMessages[groupKey];
      if (!state || state.loading || !state.hasMore) {
        return;
      }

      const element = event.currentTarget;
      const reachedBottom =
        element.scrollTop + element.clientHeight >= element.scrollHeight - 48;
      if (!reachedBottom) {
        return;
      }

      const group = groupsByKey[groupKey];
      if (!group) {
        return;
      }
      void loadGroupMessages(group, state.page + 1);
    },
    [groupMessages, groupsByKey, loadGroupMessages],
  );

  const handleBack = useCallback(() => {
    if (onBack) {
      onBack();
      return;
    }
    if (typeof window === "undefined") {
      return;
    }
    const baseUrl = getEvaluationBaseUrl();
    const hash = reportId
      ? `#report-feedback?reportId=${encodeURIComponent(reportId)}`
      : "#report-feedback";
    window.history.replaceState(null, "", `${baseUrl}${hash}`);
  }, [onBack, reportId]);

  if (!reportId) {
    return (
      <div style={{ padding: "24px" }}>
        <Card>
          <Empty description="缺少 reportId，无法加载聊天记录" />
        </Card>
      </div>
    );
  }

  return (
    <div style={{ padding: "24px" }}>
      <Card
        title={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
              返回举报详情
            </Button>
            <Text strong>用户全部聊天记录（按 user_id:agent_id 分组）</Text>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => void loadGroups()}
            loading={loadingGroups}
          >
            刷新分组
          </Button>
        }
      >
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary">
            每次按 20 轮懒加载，向下滚动加载更早记录；上滚回到最新记录。
          </Text>
        </div>

        {loadingGroups ? (
          <div style={{ textAlign: "center", padding: "48px 0" }}>
            <Spin size="large" />
          </div>
        ) : groups.length === 0 ? (
          <Empty description="该举报用户暂无聊天记录" />
        ) : (
          <Collapse
            activeKey={activeGroupKeys}
            onChange={handleCollapseChange}
            items={groups.map((group) => {
              const groupKey = buildGroupKey(group);
              const groupState = groupMessages[groupKey];
              return {
                key: groupKey,
                label: (
                  <Space wrap>
                    <Text strong>{groupKey}</Text>
                    <Tag color="blue">会话 {group.chat_count}</Tag>
                    <Tag color="purple">总轮数 {group.total_rounds}</Tag>
                    <Text type="secondary">
                      最新：
                      {group.latest_message_at
                        ? formatUtcTimeRaw(group.latest_message_at)
                        : "N/A"}
                    </Text>
                  </Space>
                ),
                children: (
                  <div
                    style={{
                      maxHeight: MESSAGES_SCROLL_HEIGHT,
                      overflowY: "auto",
                      border: "1px solid #f0f0f0",
                      borderRadius: 8,
                      padding: 12,
                      background: "#fafafa",
                    }}
                    onScroll={(event) => handleMessagesScroll(groupKey, event)}
                  >
                    {groupState?.loading &&
                    (groupState.messages.length || 0) === 0 ? (
                      <div style={{ textAlign: "center", padding: "32px 0" }}>
                        <Spin />
                      </div>
                    ) : (groupState?.messages.length || 0) === 0 ? (
                      <Empty description="该分组暂无聊天消息" />
                    ) : (
                      <>
                        {groupState?.messages.map((messageItem) => {
                          const userMessage = isUserMessage(
                            messageItem.message_type || "",
                          );
                          const generatedImageUrl = getGeneratedImageUrl(
                            messageItem.meta_data,
                          );
                          return (
                            <div
                              key={messageItem.id}
                              style={{
                                marginBottom: 12,
                                marginLeft: userMessage ? "auto" : 0,
                                marginRight: userMessage ? 0 : "auto",
                                maxWidth: "82%",
                                background: userMessage ? "#e6f7ff" : "#fff",
                                border: "1px solid #f0f0f0",
                                borderRadius: 8,
                                padding: 10,
                              }}
                            >
                              <div style={{ marginBottom: 6 }}>
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  {userMessage ? "👤 用户" : "🤖 AI"} ·{" "}
                                  {messageItem.created_at
                                    ? formatUtcTimeRaw(messageItem.created_at)
                                    : "N/A"}
                                </Text>
                              </div>
                              {messageItem.content ? (
                                <div
                                  style={{
                                    whiteSpace: "pre-wrap",
                                    wordBreak: "break-word",
                                  }}
                                >
                                  {messageItem.content}
                                </div>
                              ) : (
                                <Text type="secondary">无文本内容</Text>
                              )}
                              {messageItem.image_url && (
                                <img
                                  src={messageItem.image_url}
                                  alt="message-image"
                                  style={{
                                    marginTop: 8,
                                    maxWidth: "100%",
                                    maxHeight: 320,
                                    borderRadius: 6,
                                    border: "1px solid #eee",
                                  }}
                                />
                              )}
                              {!messageItem.image_url && generatedImageUrl && (
                                <img
                                  src={generatedImageUrl}
                                  alt="generated-image"
                                  style={{
                                    marginTop: 8,
                                    maxWidth: "100%",
                                    maxHeight: 320,
                                    borderRadius: 6,
                                    border: "1px solid #eee",
                                  }}
                                />
                              )}
                            </div>
                          );
                        })}
                        {groupState?.loading && (
                          <div
                            style={{ textAlign: "center", padding: "8px 0" }}
                          >
                            <Spin size="small" />
                          </div>
                        )}
                        {!groupState?.loading && groupState?.hasMore && (
                          <div
                            style={{ textAlign: "center", padding: "8px 0" }}
                          >
                            <Text type="secondary">继续下滑加载更早记录</Text>
                          </div>
                        )}
                        {!groupState?.loading && !groupState?.hasMore && (
                          <div
                            style={{ textAlign: "center", padding: "8px 0" }}
                          >
                            <Text type="secondary">
                              已加载全部 {groupState?.totalRounds || 0} 轮
                            </Text>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ),
              };
            })}
          />
        )}
      </Card>
    </div>
  );
};
