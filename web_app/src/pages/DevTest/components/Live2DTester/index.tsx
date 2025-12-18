/**
 * Live2DTester
 *
 * 用途：在 DevTest 页面中为 Live2D 集成预留调试面板，便于快速验证模型加载、
 * 文本驱动的嘴型动画以及动作触发逻辑。
 *
 * 使用示例：
 * ```tsx
 * import Live2DTester from './components/Live2DTester';
 *
 * <Live2DTester />
 * ```
 *
 * Props 说明：
 * - 暂无对外 Props，组件内部直接管理状态
 *
 * 注意事项：
 * - 模型文件需放置在 `public/live2d-models` 目录，详情见 `docs/LIVE2D_VIEWER_DESIGN.md`
 */
import {
  Alert,
  Button,
  Card,
  Divider,
  Form,
  Input,
  List,
  Select,
  Space,
  Switch,
  Tabs,
  Typography,
  message,
} from 'antd';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Live2DViewer, { ILive2DViewerRef } from '@/components/Live2DViewer';

import './index.less';

interface ILive2dModelOption {
  label: string;
  value: string;
  description: string;
}

interface IModel3Json {
  /** motion 定义 */
  motions?: Record<string, Array<Record<string, unknown>>>;
}

interface IMotionGroupInfo {
  /** motion 组名称 */
  group: string;
  /** 该组包含的 motion 数量 */
  count: number;
}

interface IMotionHistoryItem {
  group: string;
  index: number;
  timestamp: number;
}

const LOCAL_MODEL_OPTIONS: ILive2dModelOption[] = [
  {
    label: 'Haru (Sample)',
    value: '/live2d-models/haru/Haru.model3.json',
    description: 'Sample exported from Cubism editor, stored in public/live2d-models.',
  },
  {
    label: 'Hiyori (Sample)',
    value: '/live2d-models/Hiyori/Hiyori.model3.json',
    description: 'Another preset entry for quick smoke test.',
  },
];

const STREAMING_PLACEHOLDER =
  'LONG_PLACEHOLDER_TEXT_TO_KEEP_MOUTH_MOVING_DURING_STREAMING_RESPONSE';
const LIVE2D_DEBUG_LIP_SYNC_STORAGE_KEY = 'INTY_DEVTEST_LIVE2D_DEBUG_LIP_SYNC';

interface ILive2DInternalModel {
  settings?: IModel3Json;
}

const Live2DTester: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState<string>(LOCAL_MODEL_OPTIONS[0]?.value);
  const [inputText, setInputText] = useState<string>('');
  const [motionGroup, setMotionGroup] = useState<string>('');
  const [motionIndex, setMotionIndex] = useState<number>(0);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [viewerReady, setViewerReady] = useState<boolean>(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [motionGroups, setMotionGroups] = useState<IMotionGroupInfo[]>([]);
  const [currentMotion, setCurrentMotion] = useState<IMotionHistoryItem | null>(null);
  const [motionHistory, setMotionHistory] = useState<IMotionHistoryItem[]>([]);
  const [isMonitoring, setIsMonitoring] = useState<boolean>(false);
  const [parameterData, setParameterData] = useState<Array<{ id: string; value: number }> | null>(null);
  const [debugLipSyncEnabled, setDebugLipSyncEnabled] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem(LIVE2D_DEBUG_LIP_SYNC_STORAGE_KEY) === '1';
    } catch {
      return false;
    }
  });
  const [viewerInstanceKey, setViewerInstanceKey] = useState<number>(0);
  const viewerRef = useRef<ILive2DViewerRef | null>(null);
  const monitoringIntervalRef = useRef<number | null>(null);

  const currentModel = useMemo(
    () => LOCAL_MODEL_OPTIONS.find((option) => option.value === selectedModel),
    [selectedModel],
  );

  useEffect(() => {
    setViewerReady(false);
  }, [selectedModel]);

  const syncMotionMetadata = useCallback(() => {
    const internalSettings = (viewerRef.current?.internalModel?.internalModel as ILive2DInternalModel)?.settings;
    const groups: IMotionGroupInfo[] = Object.entries(internalSettings?.motions ?? {}).reduce<IMotionGroupInfo[]>(
      (acc, [groupName, entries]) => {
        const count = entries?.length ?? 0;
        if (count > 0) {
          acc.push({ group: groupName, count });
        }
        return acc;
      },
      [],
    );
    setMotionGroups(groups);
    if (groups.length > 0) {
      setMotionGroup(groups[0].group);
      setMotionIndex(0);
      return;
    }
    setMotionGroup('');
    setMotionIndex(0);
  }, []);

  useEffect(() => {
    if (!viewerReady) {
      setMotionGroups([]);
      setMotionGroup('');
      setMotionIndex(0);
      return;
    }
    syncMotionMetadata();
  }, [viewerReady, selectedModel, syncMotionMetadata]);

  const motionIndexOptions = useMemo(() => {
    const matchedGroup = motionGroups.find((item) => item.group === motionGroup);
    if (!matchedGroup) {
      return [];
    }
    return Array.from({ length: matchedGroup.count }, (_, index) => index);
  }, [motionGroups, motionGroup]);

  const appendLog = (messageText: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [`[${timestamp}] ${messageText}`, ...prev].slice(0, 40));
  };

  const persistDebugLipSync = (enabled: boolean) => {
    try {
      window.localStorage.setItem(LIVE2D_DEBUG_LIP_SYNC_STORAGE_KEY, enabled ? '1' : '0');
    } catch {
      // ignore
    }
  };

  const handleSpeakOnce = () => {
    if (!inputText.trim()) {
      message.warning('Please enter the simulated response text.');
      return;
    }
    viewerRef.current?.speakText(inputText.trim());
    appendLog(`Triggered speakText (${inputText.length} chars).`);
  };

  const handleStartStreaming = () => {
    if (isStreaming) {
      return;
    }
    setIsStreaming(true);
    viewerRef.current?.speakText(STREAMING_PLACEHOLDER);
    appendLog('Streaming simulation started.');
  };

  const handleStopStreaming = () => {
    setIsStreaming(false);
    viewerRef.current?.stopSpeaking();
    appendLog('Streaming simulation stopped.');
  };

  const handleTriggerMotion = () => {
    if (!motionGroup.trim()) {
      message.warning('Motion group cannot be empty.');
      return;
    }
    viewerRef.current?.motion(motionGroup.trim(), motionIndex);
    appendLog(`Triggered motion ${motionGroup}#${motionIndex}.`);
    const motionInfo: IMotionHistoryItem = {
      group: motionGroup.trim(),
      index: motionIndex,
      timestamp: Date.now(),
    };
    setCurrentMotion(motionInfo);
    setMotionHistory((prev) => [motionInfo, ...prev].slice(0, 20));
  };

  const startMonitoring = () => {
    if (monitoringIntervalRef.current) {
      return;
    }
    setIsMonitoring(true);
    const interval = window.setInterval(() => {
      if (!viewerRef.current) {
        return;
      }
      const motion = viewerRef.current.getCurrentMotion();
      if (motion) {
        const motionInfo: IMotionHistoryItem = {
          group: motion.group ?? '',
          index: motion.index ?? 0,
          timestamp: motion.timestamp,
        };
        setCurrentMotion(motionInfo);
        const params = viewerRef.current.getAllParameters();
        if (params) {
          setParameterData(params);
        }
      }
    }, 100);
    monitoringIntervalRef.current = interval;
    appendLog('Motion monitoring started.');
  };

  const stopMonitoring = () => {
    if (monitoringIntervalRef.current) {
      clearInterval(monitoringIntervalRef.current);
      monitoringIntervalRef.current = null;
    }
    setIsMonitoring(false);
    appendLog('Motion monitoring stopped.');
  };

  useEffect(() => {
    return () => {
      if (monitoringIntervalRef.current) {
        clearInterval(monitoringIntervalRef.current);
      }
    };
  }, []);

  return (
    <div className="live2d-tester">
      <Alert
        type="info"
        showIcon
        message="Place your Live2D exports inside public/live2d-models to mirror the production CDN layout."
      />
      <div className="live2d-tester__workspace">
        <Card title="Control Panel" className="live2d-tester__panel">
          <Form layout="vertical">
            <Form.Item label="Model selector">
              <Select
                options={LOCAL_MODEL_OPTIONS}
                value={selectedModel}
                onChange={setSelectedModel}
              />
              {currentModel?.description ? (
                <Typography.Paragraph type="secondary" className="live2d-tester__hint">
                  {currentModel.description}
                </Typography.Paragraph>
              ) : null}
            </Form.Item>

            <Divider />

            <Form.Item label="Simulated response text">
              <Input.TextArea
                rows={4}
                placeholder="Type any text to drive the sine-wave mouth animation."
                value={inputText}
                onChange={(event) => setInputText(event.target.value)}
              />
              <Space className="live2d-tester__button-group">
                <Button type="primary" onClick={handleSpeakOnce} disabled={!viewerReady}>
                  Trigger speakText
                </Button>
                <Button
                  danger={isStreaming}
                  disabled={!viewerReady}
                  onClick={isStreaming ? handleStopStreaming : handleStartStreaming}
                >
                  {isStreaming ? 'Stop streaming' : 'Start streaming simulation'}
                </Button>
              </Space>
            </Form.Item>

            <Divider />

            <Form.Item
              label="DevTest: Lip sync debug verification"
              extra={`Enable parameter read-back verification in Live2DViewer. You can also use ?live2dDebugLipSync=1 in URL.`}
            >
              <Space>
                <Switch
                  checked={debugLipSyncEnabled}
                  onChange={(checked) => {
                    setDebugLipSyncEnabled(checked);
                    persistDebugLipSync(checked);
                    setViewerInstanceKey((prev) => prev + 1);
                    appendLog(`Lip sync debug verification ${checked ? 'enabled' : 'disabled'}. Viewer reloaded.`);
                    message.info('Lip sync debug setting updated. Viewer reloaded.');
                  }}
                />
                <Typography.Text type="secondary">
                  {debugLipSyncEnabled ? 'Enabled' : 'Disabled'}
                </Typography.Text>
              </Space>
            </Form.Item>

            <Form.Item label="Motion group">
              <Select<string>
                placeholder="Select motion group"
                options={motionGroups.map((groupInfo) => ({
                  label: `${groupInfo.group} (${groupInfo.count})`,
                  value: groupInfo.group,
                }))}
                value={motionGroup || undefined}
                disabled={!motionGroups.length}
                onChange={(value) => setMotionGroup(value)}
              />
            </Form.Item>

            <Form.Item label="Motion index">
              <Select<number>
                placeholder="Select motion index"
                options={motionIndexOptions.map((index) => ({
                  label: `Motion #${index}`,
                  value: index,
                }))}
                value={motionIndexOptions.includes(motionIndex) ? motionIndex : undefined}
                onChange={(value) => setMotionIndex(value)}
                disabled={!motionIndexOptions.length}
              />
            </Form.Item>

            <Button onClick={handleTriggerMotion} block disabled={!viewerReady}>
              Trigger motion
            </Button>
          </Form>
        </Card>

        <Card title="Viewer">
          <div className="live2d-tester__viewer">
            <Live2DViewer
              key={viewerInstanceKey}
              ref={viewerRef}
              modelUrl={selectedModel}
              scale={0.2}
              x={0}
              y={0}
              onReady={() => {
                setViewerReady(true);
                appendLog(`Model ready: ${selectedModel}`);
              }}
            />
          </div>
          <Typography.Paragraph type="secondary" className="live2d-tester__hint">
            Assets resolve from <code>public/live2d-models</code>. Update the selector above to swap
            between different exports.
          </Typography.Paragraph>
        </Card>
      </div>

      <Card>
        <Tabs
          defaultActiveKey="logs"
          items={[
            {
              key: 'logs',
              label: 'Action logs',
              children: (
                <List
                  dataSource={logs}
                  locale={{ emptyText: 'No actions yet.' }}
                  renderItem={(item) => <List.Item>{item}</List.Item>}
                  size="small"
                />
              ),
            },
            {
              key: 'monitor',
              label: 'Motion Monitor',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Button
                      type={isMonitoring ? 'default' : 'primary'}
                      onClick={isMonitoring ? stopMonitoring : startMonitoring}
                      disabled={!viewerReady}
                    >
                      {isMonitoring ? 'Stop monitoring' : 'Start monitoring'}
                    </Button>
                    <Button
                      onClick={() => {
                        setMotionHistory([]);
                        setCurrentMotion(null);
                        setParameterData(null);
                      }}
                      disabled={!isMonitoring}
                    >
                      Clear history
                    </Button>
                  </Space>

                  <Divider style={{ margin: '12px 0' }} />

                  <div>
                    <Typography.Text strong>Current Motion:</Typography.Text>
                    {currentMotion ? (
                      <div style={{ marginTop: 8 }}>
                        <Typography.Text code>
                          {currentMotion.group}#{currentMotion.index}
                        </Typography.Text>
                        <Typography.Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                          {new Date(currentMotion.timestamp).toLocaleTimeString()}
                        </Typography.Text>
                      </div>
                    ) : (
                      <Typography.Text type="secondary" style={{ marginLeft: 8 }}>
                        No motion playing
                      </Typography.Text>
                    )}
                  </div>

                  <Divider style={{ margin: '12px 0' }} />

                  <div>
                    <Typography.Text strong>Motion History:</Typography.Text>
                    <List
                      dataSource={motionHistory}
                      locale={{ emptyText: 'No motion history' }}
                      renderItem={(item, index) => (
                        <List.Item style={{ padding: '4px 0' }}>
                          <Typography.Text code>
                            {item.group}#{item.index}
                          </Typography.Text>
                          <Typography.Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                            {new Date(item.timestamp).toLocaleTimeString()}
                          </Typography.Text>
                        </List.Item>
                      )}
                      size="small"
                      style={{ maxHeight: 200, overflowY: 'auto', marginTop: 8 }}
                    />
                  </div>

                  {parameterData && parameterData.length > 0 && (
                    <>
                      <Divider style={{ margin: '12px 0' }} />
                      <div>
                        <Typography.Text strong>Parameters ({parameterData.length}):</Typography.Text>
                        <List
                          dataSource={parameterData.filter((p) => Math.abs(p.value) > 0.01).slice(0, 10)}
                          locale={{ emptyText: 'No active parameters' }}
                          renderItem={(item) => (
                            <List.Item style={{ padding: '4px 0' }}>
                              <Typography.Text code style={{ fontSize: 11 }}>
                                {item.id}
                              </Typography.Text>
                              <Typography.Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                                {item.value.toFixed(3)}
                              </Typography.Text>
                            </List.Item>
                          )}
                          size="small"
                          style={{ maxHeight: 150, overflowY: 'auto', marginTop: 8 }}
                        />
                      </div>
                    </>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default Live2DTester;


