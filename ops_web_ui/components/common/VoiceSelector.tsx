/**
 * 音色选择器组件
 * 用于在角色创建/编辑时选择音色
 */

import React, {
  useState,
  useCallback,
  useMemo,
  useEffect,
  useRef,
} from "react";
import {
  Card,
  Input,
  Select,
  Button,
  Row,
  Col,
  Empty,
  message,
  Spin,
  Tag,
  Space,
  Badge,
  Tooltip,
  Avatar,
} from "antd";
import {
  SearchOutlined,
  ReloadOutlined,
  SoundOutlined,
  PlayCircleOutlined,
  ClearOutlined,
} from "@ant-design/icons";
import api from "../../services/api";
import type { Voice } from "../../types";
import {
  filterVoicesByGender,
  getVoiceGenderStats,
  getNormalizedVoiceGender,
  mapImateGenderToVoiceGenderFilter,
  type VoiceGenderFilter,
} from "../../utils/voiceFilters";
import VoicePreviewPlayer from "./VoicePreviewPlayer";

const { Search } = Input;
const { Option } = Select;

interface VoiceSelectorProps {
  value?: string;
  onChange?: (voiceId: string | undefined) => void;
  disabled?: boolean;
  placeholder?: string;
  imateGender?: string;
}

export const VoiceSelector: React.FC<VoiceSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  imateGender,
}) => {
  const requiredGenderFilter = useMemo(
    () => mapImateGenderToVoiceGenderFilter(imateGender),
    [imateGender],
  );
  // 状态管理
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [providerFilter, setProviderFilter] = useState<string>("all");
  const [genderFilter, setGenderFilter] =
    useState<VoiceGenderFilter>(requiredGenderFilter);
  const [expanded, setExpanded] = useState(false);
  const [selectedVoiceInfo, setSelectedVoiceInfo] = useState<Voice | null>(
    null,
  );
  const latestLoadRequestIdRef = useRef(0);

  // 加载音色列表
  const loadVoices = useCallback(
    async (
      forceRefresh = false,
      search = "",
      source = "all",
      provider = "all",
      gender: VoiceGenderFilter = "all",
    ) => {
      const requestId = ++latestLoadRequestIdRef.current;
      setLoading(true);
      try {
        const params: { search?: string; provider?: string } = {
          // 移除page_size限制，让后端返回所有音色
        };
        if (search) params.search = search;
        // 后端支持 provider 筛选
        if (provider !== "all") params.provider = provider;

        const voiceList = await api.voices.listVoices(params);
        let filteredVoices = voiceList || [];

        // 前端source筛选 - 使用后端返回的voice_type字段
        if (source !== "all") {
          filteredVoices = filteredVoices.filter((voice) => {
            if (source === "personal") {
              return voice.voice_type === "personal";
            } else if (source === "preset") {
              return voice.voice_type === "preset";
            }
            return true;
          });
        }

        filteredVoices = filterVoicesByGender(filteredVoices, gender);

        if (requestId !== latestLoadRequestIdRef.current) {
          return;
        }

        setVoices(filteredVoices);

        if (forceRefresh) {
          message.success("音色列表已刷新");
        }
      } catch (error) {
        if (requestId !== latestLoadRequestIdRef.current) {
          return;
        }
        console.error("加载音色列表失败:", error);
        message.error("加载音色列表失败");
        setVoices([]);
      } finally {
        if (requestId === latestLoadRequestIdRef.current) {
          setLoading(false);
        }
      }
    },
    [],
  );

  // 根据 voice_id 加载单个音色详情
  const loadVoiceById = useCallback(
    async (voiceId: string) => {
      if (!voiceId) return null;

      try {
        // 首先尝试从当前列表中查找
        const existingVoice = voices.find(
          (voice) => voice.voice_id === voiceId,
        );
        if (existingVoice) {
          setSelectedVoiceInfo(existingVoice);
          return existingVoice;
        }

        // 尝试加载完整的音色列表来查找目标音色
        const allVoices = await api.voices.listVoices({});
        const foundVoice = allVoices?.find(
          (voice) => voice.voice_id === voiceId,
        );
        if (foundVoice) {
          setSelectedVoiceInfo(foundVoice);
          return foundVoice;
        }

        // 如果还是找不到，更新为最终的基本音色信息
        const finalVoiceInfo = {
          voice_id: voiceId,
          name: voiceId, // 使用 voice_id 作为显示名称
          category: "unknown",
          description: "已选择的音色",
        };
        setSelectedVoiceInfo(finalVoiceInfo);
        return finalVoiceInfo;
      } catch (error) {
        console.error("获取音色详情失败:", error);

        // 出错时更新为错误状态的音色信息
        const errorVoiceInfo = {
          voice_id: voiceId,
          name: voiceId,
          category: "error",
          description: "音色加载失败",
        };
        setSelectedVoiceInfo(errorVoiceInfo);
        return errorVoiceInfo;
      }
    },
    [voices],
  );

  // 搜索防抖处理
  const debouncedLoadVoices = useMemo(() => {
    const debounce = <TArgs extends unknown[]>(
      func: (...args: TArgs) => void,
      delay: number,
    ) => {
      let timeoutId: ReturnType<typeof setTimeout>;
      return (...args: TArgs) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
      };
    };
    return debounce(
      (
        search: string,
        source: string,
        provider: string,
        gender: VoiceGenderFilter,
      ) => {
        loadVoices(false, search, source, provider, gender);
      },
      500,
    );
  }, [loadVoices]);

  // 初始加载
  useEffect(() => {
    loadVoices(false, "", "all", "all", requiredGenderFilter);
  }, [loadVoices, requiredGenderFilter]);

  useEffect(() => {
    setGenderFilter(requiredGenderFilter);
  }, [requiredGenderFilter]);

  // 当 value 变化时，立即显示基本信息并异步加载详细信息
  useEffect(() => {
    if (value) {
      // 立即设置基本音色信息用于显示
      const basicInfo = {
        voice_id: value,
        name: value,
        category: "loading",
        description: "正在加载音色信息...",
      };
      setSelectedVoiceInfo(basicInfo);

      // 异步加载完整音色信息
      loadVoiceById(value);
    } else {
      setSelectedVoiceInfo(null);
    }
  }, [value, loadVoiceById]);

  useEffect(() => {
    if (!value || !selectedVoiceInfo || selectedVoiceInfo.voice_id !== value) {
      return;
    }
    if (requiredGenderFilter === "all") {
      return;
    }
    const selectedVoiceGender = getNormalizedVoiceGender(selectedVoiceInfo);
    if (
      selectedVoiceGender !== requiredGenderFilter &&
      selectedVoiceGender !== "unknown"
    ) {
      message.warning("当前音色与角色性别不匹配，已自动清除，请重新选择");
      onChange?.(undefined);
      setSelectedVoiceInfo(null);
    }
  }, [value, selectedVoiceInfo, requiredGenderFilter, onChange]);

  // 搜索和筛选变化时的防抖处理
  useEffect(() => {
    debouncedLoadVoices(searchText, sourceFilter, providerFilter, genderFilter);
  }, [
    searchText,
    sourceFilter,
    providerFilter,
    genderFilter,
    debouncedLoadVoices,
  ]);

  // 获取当前选中的音色
  const selectedVoice = useMemo(() => {
    // 优先使用专门加载的选中音色信息
    if (selectedVoiceInfo && selectedVoiceInfo.voice_id === value) {
      return selectedVoiceInfo;
    }
    // 否则从音色列表中查找
    return voices.find((voice) => voice.voice_id === value);
  }, [voices, value, selectedVoiceInfo]);

  // 获取音色来源统计 - 使用后端返回的voice_type和provider字段
  const voiceStats = useMemo(() => {
    const genderStats = getVoiceGenderStats(voices);
    const stats = {
      personal: 0,
      preset: 0,
      total: voices.length,
      gemini: 0,
      elevenlabs: 0,
      male: genderStats.male,
      female: genderStats.female,
      unknown: genderStats.unknown,
    };
    voices.forEach((voice) => {
      if (voice.voice_type === "personal") {
        stats.personal++;
      } else if (voice.voice_type === "preset") {
        stats.preset++;
      }
      if (voice.provider === "gemini") {
        stats.gemini++;
      } else if (voice.provider === "elevenlabs") {
        stats.elevenlabs++;
      }
    });
    return stats;
  }, [voices]);

  // 选择音色
  const handleSelectVoice = useCallback(
    (voiceId: string) => {
      if (disabled) return;

      if (value === voiceId) {
        // 如果点击已选中的音色，则取消选择
        onChange?.(undefined);
      } else {
        onChange?.(voiceId);
      }
    },
    [value, onChange, disabled],
  );

  // 清除选择
  const handleClearSelection = useCallback(() => {
    if (disabled) return;
    onChange?.(undefined);
  }, [onChange, disabled]);

  // 音色卡片组件
  const VoiceCard: React.FC<{ voice: Voice }> = ({ voice }) => {
    const isSelected = value === voice.voice_id;
    const normalizedGender = getNormalizedVoiceGender(voice);

    return (
      <Card
        size="small"
        hoverable={!disabled}
        className={`voice-card ${isSelected ? "voice-card-selected" : ""}`}
        style={{
          borderColor: isSelected ? "#1890ff" : "#f0f0f0",
          backgroundColor: isSelected ? "#f6ffed" : "#fff",
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.6 : 1,
          transition: "all 0.3s ease",
        }}
        onClick={() => handleSelectVoice(voice.voice_id)}
        bodyStyle={{ padding: "12px" }}
      >
        <div style={{ textAlign: "center" }}>
          <Avatar
            size={48}
            icon={<SoundOutlined />}
            style={{
              backgroundColor: isSelected ? "#52c41a" : "#1890ff",
              marginBottom: 8,
            }}
          />

          <div style={{ marginBottom: 4 }}>
            <Tooltip title={voice.name}>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: "14px",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  color: isSelected ? "#52c41a" : "#333",
                }}
              >
                {voice.name}
              </div>
            </Tooltip>
          </div>

          <Space size={4} style={{ marginBottom: 4 }} wrap>
            {voice.provider && (
              <Tag
                color={voice.provider === "gemini" ? "green" : "blue"}
                style={{ margin: 0 }}
              >
                {voice.provider === "gemini" ? "Gemini" : "ElevenLabs"}
              </Tag>
            )}
            {voice.category && (
              <Tag
                color={isSelected ? "success" : "default"}
                style={{ margin: 0 }}
              >
                {voice.category}
              </Tag>
            )}
            {voice.gender && (
              <Tag
                color={
                  normalizedGender === "female"
                    ? "magenta"
                    : normalizedGender === "male"
                      ? "cyan"
                      : "default"
                }
                style={{ margin: 0 }}
              >
                {normalizedGender === "female"
                  ? "女"
                  : normalizedGender === "male"
                    ? "男"
                    : "未知"}
              </Tag>
            )}
          </Space>

          {/* 预览播放按钮 */}
          <div
            style={{
              marginTop: 8,
              padding: "4px 0",
              borderTop: "1px solid #f0f0f0",
            }}
            onClick={(e) => e.stopPropagation()} // 阻止事件冒泡，避免触发选择
          >
            <VoicePreviewPlayer
              previewUrl={voice.preview_url}
              voiceName={voice.name}
              size="small"
              style={{
                width: "100%",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                height: "28px",
                borderRadius: "4px",
                backgroundColor: voice.preview_url ? "#f6ffed" : "#fafafa",
                border: voice.preview_url
                  ? "1px solid #d9f7be"
                  : "1px solid #f0f0f0",
              }}
            />
          </div>

          {voice.description && (
            <div
              style={{
                fontSize: "12px",
                color: "#666",
                lineHeight: "1.2",
                height: "24px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
              }}
            >
              {voice.description}
            </div>
          )}

          {/* 音色试听按钮 - 如果有样本的话 */}
          {voice.samples && voice.samples.length > 0 && (
            <Button
              type="text"
              size="small"
              icon={<PlayCircleOutlined />}
              style={{
                marginTop: 4,
                fontSize: "12px",
                padding: "0 4px",
                height: "20px",
              }}
              onClick={(e) => {
                e.stopPropagation();
                // TODO: 实现音色试听功能
                message.info("音色试听功能开发中");
              }}
            >
              试听
            </Button>
          )}
        </div>
      </Card>
    );
  };

  return (
    <div className="voice-selector">
      {/* 当前选中音色显示 */}
      {selectedVoice && (
        <div style={{ marginBottom: 16 }}>
          <Space align="center">
            {selectedVoice.category === "loading" ? (
              <Badge status="processing" />
            ) : selectedVoice.category === "error" ? (
              <Badge status="error" />
            ) : (
              <Badge status="success" />
            )}
            <span style={{ fontWeight: 500 }}>当前音色：</span>
            <Tag
              color={
                selectedVoice.category === "loading"
                  ? "blue"
                  : selectedVoice.category === "error"
                    ? "red"
                    : "green"
              }
              icon={<SoundOutlined />}
            >
              {selectedVoice.name}
              {selectedVoice.category === "loading" && (
                <Spin size="small" style={{ marginLeft: 4 }} />
              )}
            </Tag>
            {selectedVoice.description &&
              selectedVoice.category !== "loading" && (
                <span style={{ fontSize: "12px", color: "#666" }}>
                  ({selectedVoice.description})
                </span>
              )}
            {!disabled && (
              <Button
                type="text"
                size="small"
                icon={<ClearOutlined />}
                onClick={handleClearSelection}
              >
                清除
              </Button>
            )}
          </Space>
        </div>
      )}

      {/* 搜索和过滤控件 */}
      <div style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col span={7}>
            <Search
              placeholder="搜索音色名称"
              allowClear
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              disabled={disabled}
              prefix={<SearchOutlined />}
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder="音色类型"
              style={{ width: "100%" }}
              value={sourceFilter}
              onChange={setSourceFilter}
              disabled={disabled}
            >
              <Option value="all">全部类型 ({voiceStats.total})</Option>
              <Option value="personal">个人音色 ({voiceStats.personal})</Option>
              <Option value="preset">预置音色 ({voiceStats.preset})</Option>
            </Select>
          </Col>
          <Col span={4}>
            <Select
              placeholder="TTS 服务商"
              style={{ width: "100%" }}
              value={providerFilter}
              onChange={setProviderFilter}
              disabled={disabled}
            >
              <Option value="all">全部服务商</Option>
              <Option value="gemini">
                <Tag color="green" style={{ marginRight: 4 }}>
                  Gemini
                </Tag>
                ({voiceStats.gemini})
              </Option>
              <Option value="elevenlabs">
                <Tag color="blue" style={{ marginRight: 4 }}>
                  ElevenLabs
                </Tag>
                ({voiceStats.elevenlabs})
              </Option>
            </Select>
          </Col>
          <Col span={4}>
            <Select
              placeholder="性别"
              style={{ width: "100%" }}
              value={genderFilter}
              onChange={setGenderFilter}
              disabled={disabled || requiredGenderFilter !== "all"}
            >
              <Option value="all">全部性别 ({voiceStats.total})</Option>
              <Option value="male">男 ({voiceStats.male})</Option>
              <Option value="female">女 ({voiceStats.female})</Option>
              <Option value="unknown">未知 ({voiceStats.unknown})</Option>
            </Select>
          </Col>
          <Col span={5}>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={() =>
                  loadVoices(
                    true,
                    searchText,
                    sourceFilter,
                    providerFilter,
                    genderFilter,
                  )
                }
                loading={loading}
                disabled={disabled}
              >
                刷新
              </Button>
              <Button
                type="link"
                size="small"
                onClick={() => setExpanded(!expanded)}
                disabled={disabled}
              >
                {expanded ? "收起" : "展开"}
              </Button>
            </Space>
          </Col>
        </Row>
        {requiredGenderFilter !== "all" && (
          <div style={{ marginTop: 8, fontSize: "12px", color: "#666" }}>
            音色已按角色性别自动筛选，仅显示匹配音色
          </div>
        )}
      </div>

      {/* 音色列表 */}
      <Spin spinning={loading}>
        {voices.length === 0 ? (
          <Empty
            description={searchText ? "没有找到匹配的音色" : "暂无音色数据"}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ padding: "40px 20px" }}
          />
        ) : (
          <div
            style={{
              maxHeight: expanded ? "none" : "300px",
              overflowY: expanded ? "visible" : "auto",
              border: "1px solid #f0f0f0",
              borderRadius: "6px",
              padding: "12px",
              backgroundColor: "#fafafa",
            }}
          >
            <Row gutter={[12, 12]}>
              {voices.map((voice) => (
                <Col key={voice.voice_id} xs={24} sm={12} md={8} lg={6} xl={4}>
                  <VoiceCard voice={voice} />
                </Col>
              ))}
            </Row>

            {!expanded && voices.length > 8 && (
              <div style={{ textAlign: "center", marginTop: 12 }}>
                <Button
                  type="link"
                  onClick={() => setExpanded(true)}
                  disabled={disabled}
                >
                  显示全部 {voices.length} 个音色
                </Button>
              </div>
            )}
          </div>
        )}
      </Spin>

      {/* 统计信息 */}
      {voices.length > 0 && (
        <div
          style={{
            marginTop: 12,
            fontSize: "12px",
            color: "#666",
            textAlign: "center",
          }}
        >
          共找到 {voices.length} 个音色
          {voiceStats.gemini > 0 && voiceStats.elevenlabs > 0 && (
            <span>
              {" "}
              (Gemini: {voiceStats.gemini}, ElevenLabs: {voiceStats.elevenlabs})
            </span>
          )}
          {selectedVoice && ` • 已选择：${selectedVoice.name}`}
        </div>
      )}

      {/* 自定义样式 */}
      <style>{`
        .voice-card-selected {
          box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2) !important;
        }
        
        .voice-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .voice-card-selected:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3) !important;
        }
      `}</style>
    </div>
  );
};

export default VoiceSelector;
