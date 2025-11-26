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
  InputNumber,
  List,
  Select,
  Space,
  Typography,
  message,
} from 'antd';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import Live2DViewer, { ILive2DViewerRef } from '@/components/Live2DViewer';

import './index.less';

interface ILive2dModelOption {
  label: string;
  value: string;
  description: string;
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

const Live2DTester: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState<string>(LOCAL_MODEL_OPTIONS[0]?.value);
  const [inputText, setInputText] = useState<string>('');
  const [motionGroup, setMotionGroup] = useState<string>('TapBody');
  const [motionIndex, setMotionIndex] = useState<number>(0);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [viewerReady, setViewerReady] = useState<boolean>(false);
  const [logs, setLogs] = useState<string[]>([]);
  const viewerRef = useRef<ILive2DViewerRef | null>(null);

  const currentModel = useMemo(
    () => LOCAL_MODEL_OPTIONS.find((option) => option.value === selectedModel),
    [selectedModel],
  );

  useEffect(() => {
    setViewerReady(false);
  }, [selectedModel]);

  const appendLog = (messageText: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [`[${timestamp}] ${messageText}`, ...prev].slice(0, 40));
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
  };

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

            <Form.Item label="Motion group">
              <Input
                placeholder="TapBody / Idle / custom motion group name"
                value={motionGroup}
                onChange={(event) => setMotionGroup(event.target.value)}
              />
            </Form.Item>

            <Form.Item label="Motion index">
              <InputNumber min={0} value={motionIndex} onChange={(value) => setMotionIndex(value ?? 0)} />
            </Form.Item>

            <Button onClick={handleTriggerMotion} block disabled={!viewerReady}>
              Trigger motion
            </Button>
          </Form>
        </Card>

        <Card title="Viewer">
          <div className="live2d-tester__viewer">
            <Live2DViewer
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

      <Card title="Action logs">
        <List
          dataSource={logs}
          locale={{ emptyText: 'No actions yet.' }}
          renderItem={(item) => <List.Item>{item}</List.Item>}
          size="small"
        />
      </Card>
    </div>
  );
};

export default Live2DTester;


