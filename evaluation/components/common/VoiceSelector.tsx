/**
 * 音色选择器组件
 * 用于在角色创建/编辑时选择音色
 */

import React, { useState, useCallback, useMemo, useEffect } from "react";
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
  UserOutlined,
} from "@ant-design/icons";
import api from "../../services/api";
import type { Voice } from "../../types";
import VoicePreviewPlayer from "./VoicePreviewPlayer";

const { Search } = Input;
const { Option } = Select;

interface VoiceSelectorProps {
  value?: string;
  onChange?: (voiceId: string | undefined) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const VoiceSelector: React.FC<VoiceSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  placeholder = "请选择音色",
}) => {
  // 状态管理
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [expanded, setExpanded] = useState(false);

  // 加载音色列表
  const loadVoices = useCallback(async (forceRefresh = false, search = "", category = "all") => {
    setLoading(true);
    try {
      const params: any = {};
      if (search) params.search = search;
      if (category !== "all") params.category = category;
      
      const voiceList = await api.voices.listVoices(params);
      setVoices(voiceList || []);
      
      if (forceRefresh) {
        message.success("音色列表已刷新");
      }
    } catch (error) {
      console.error("加载音色列表失败:", error);
      message.error("加载音色列表失败");
      setVoices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 搜索防抖处理
  const debouncedLoadVoices = useMemo(() => {
    const debounce = (func: Function, delay: number) => {
      let timeoutId: NodeJS.Timeout;
      return (...args: any[]) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
      };
    };
    return debounce((search: string, category: string) => {
      loadVoices(false, search, category);
    }, 500);
  }, [loadVoices]);

  // 初始加载
  useEffect(() => {
    loadVoices(false, searchText, categoryFilter);
  }, []); // 只在组件挂载时加载一次

  // 搜索和筛选变化时的防抖处理
  useEffect(() => {
    debouncedLoadVoices(searchText, categoryFilter);
  }, [searchText, categoryFilter, debouncedLoadVoices]);

  // 获取当前选中的音色
  const selectedVoice = useMemo(() => {
    return voices.find(voice => voice.voice_id === value);
  }, [voices, value]);

  // 获取音色分类列表
  const categories = useMemo(() => {
    const categorySet = new Set<string>();
    voices.forEach(voice => {
      if (voice.category) {
        categorySet.add(voice.category);
      }
    });
    return Array.from(categorySet).sort();
  }, [voices]);

  // 选择音色
  const handleSelectVoice = useCallback((voiceId: string) => {
    if (disabled) return;
    
    if (value === voiceId) {
      // 如果点击已选中的音色，则取消选择
      onChange?.(undefined);
    } else {
      onChange?.(voiceId);
    }
  }, [value, onChange, disabled]);

  // 清除选择
  const handleClearSelection = useCallback(() => {
    if (disabled) return;
    onChange?.(undefined);
  }, [onChange, disabled]);

  // 音色卡片组件
  const VoiceCard: React.FC<{ voice: Voice }> = ({ voice }) => {
    const isSelected = value === voice.voice_id;
    
    return (
      <Card
        size="small"
        hoverable={!disabled}
        className={`voice-card ${isSelected ? 'voice-card-selected' : ''}`}
        style={{
          borderColor: isSelected ? '#1890ff' : '#f0f0f0',
          backgroundColor: isSelected ? '#f6ffed' : '#fff',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.6 : 1,
          transition: 'all 0.3s ease',
        }}
        onClick={() => handleSelectVoice(voice.voice_id)}
        bodyStyle={{ padding: '12px' }}
      >
        <div style={{ textAlign: 'center' }}>
          <Avatar
            size={48}
            icon={<SoundOutlined />}
            style={{
              backgroundColor: isSelected ? '#52c41a' : '#1890ff',
              marginBottom: 8,
            }}
          />
          
          <div style={{ marginBottom: 4 }}>
            <Tooltip title={voice.name}>
              <div 
                style={{
                  fontWeight: 600,
                  fontSize: '14px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  color: isSelected ? '#52c41a' : '#333',
                }}
              >
                {voice.name}
              </div>
            </Tooltip>
          </div>

          {voice.category && (
            <Tag 
              size="small" 
              color={isSelected ? 'green' : 'blue'}
              style={{ marginBottom: 4 }}
            >
              {voice.category}
            </Tag>
          )}

          {/* 预览播放按钮 */}
          <div 
            style={{ 
              marginTop: 8,
              padding: '4px 0',
              borderTop: '1px solid #f0f0f0',
            }}
            onClick={(e) => e.stopPropagation()} // 阻止事件冒泡，避免触发选择
          >
            <VoicePreviewPlayer
              previewUrl={voice.preview_url}
              voiceName={voice.name}
              size="small"
              style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '28px',
                borderRadius: '4px',
                backgroundColor: voice.preview_url ? '#f6ffed' : '#fafafa',
                border: voice.preview_url ? '1px solid #d9f7be' : '1px solid #f0f0f0',
              }}
            />
          </div>

          {voice.description && (
            <div
              style={{
                fontSize: '12px',
                color: '#666',
                lineHeight: '1.2',
                height: '24px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
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
                fontSize: '12px',
                padding: '0 4px',
                height: '20px',
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
            <Badge status="success" />
            <span style={{ fontWeight: 500 }}>当前音色：</span>
            <Tag color="green" icon={<SoundOutlined />}>
              {selectedVoice.name}
            </Tag>
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
          <Col span={10}>
            <Search
              placeholder="搜索音色名称"
              allowClear
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              disabled={disabled}
              prefix={<SearchOutlined />}
            />
          </Col>
          <Col span={8}>
            <Select
              placeholder="选择分类"
              style={{ width: '100%' }}
              value={categoryFilter}
              onChange={setCategoryFilter}
              disabled={disabled}
            >
              <Option value="all">全部分类</Option>
              {categories.map(category => (
                <Option key={category} value={category}>
                  {category}
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={6}>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => loadVoices(true, searchText, categoryFilter)}
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
                {expanded ? '收起' : '展开'}
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      {/* 音色列表 */}
      <Spin spinning={loading}>
        {voices.length === 0 ? (
          <Empty
            description={searchText ? "没有找到匹配的音色" : "暂无音色数据"}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ padding: '40px 20px' }}
          />
        ) : (
          <div
            style={{
              maxHeight: expanded ? 'none' : '300px',
              overflowY: expanded ? 'visible' : 'auto',
              border: '1px solid #f0f0f0',
              borderRadius: '6px',
              padding: '12px',
              backgroundColor: '#fafafa',
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
              <div style={{ textAlign: 'center', marginTop: 12 }}>
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
        <div style={{ marginTop: 12, fontSize: '12px', color: '#666', textAlign: 'center' }}>
          共找到 {voices.length} 个音色
          {selectedVoice && ` • 已选择：${selectedVoice.name}`}
        </div>
      )}

      {/* 自定义样式 */}
      <style jsx>{`
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