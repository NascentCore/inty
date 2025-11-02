import React, { useState, useEffect } from 'react';
import { Button, Input, Space, message, Alert } from 'antd';
import { saveToken, clearToken, getToken } from '@/utils/token';
import { logger } from '@/utils/logger';

/**
 * Token 写入组件
 * 用于手动写入和管理 API Token
 */
const TokenWriter: React.FC = () => {
  const [token, setToken] = useState<string>('');
  const [currentToken, setCurrentToken] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  /**
   * 加载当前已保存的 token
   */
  const loadCurrentToken = async () => {
    try {
      const savedToken = await getToken();
      setCurrentToken(savedToken || '');
    } catch (error) {
      logger.error('加载 Token 失败', error);
    }
  };

  /**
   * 组件挂载时加载当前 token
   */
  useEffect(() => {
    loadCurrentToken();
  }, []);

  /**
   * 保存 Token
   */
  const handleSaveToken = async () => {
    if (!token.trim()) {
      message.warning('请输入 Token');
      return;
    }

    setLoading(true);
    try {
      await saveToken(token.trim());
      await loadCurrentToken();
      setToken('');
      message.success('Token 已保存');
      logger.testSuccess('Token 写入成功', token.trim());
    } catch (error) {
      logger.error('保存 Token 失败', error);
      message.error('保存 Token 失败');
    } finally {
      setLoading(false);
    }
  };

  /**
   * 清除 Token
   */
  const handleClearToken = async () => {
    setLoading(true);
    try {
      await clearToken();
      await loadCurrentToken();
      setToken('');
      message.success('Token 已清除');
      logger.testSuccess('Token 已清除');
    } catch (error) {
      logger.error('清除 Token 失败', error);
      message.error('清除 Token 失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="test-component">
      <h4>写入 Token</h4>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 当前 Token 显示 */}
        {currentToken && (
          <Alert
            message="当前已保存的 Token"
            description={
              <div style={{ wordBreak: 'break-all', fontFamily: 'monospace' }}>
                {currentToken}
              </div>
            }
            type="info"
            showIcon
          />
        )}

        {/* Token 输入框 */}
        <div>
          <label>输入 Token:</label>
          <Input.TextArea
            placeholder="请输入 API Token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            rows={3}
            style={{ marginTop: 8 }}
          />
        </div>

        {/* 操作按钮 */}
        <Space>
          <Button
            type="primary"
            onClick={handleSaveToken}
            loading={loading}
            disabled={!token.trim()}
          >
            保存 Token
          </Button>
          <Button
            danger
            onClick={handleClearToken}
            loading={loading}
            disabled={!currentToken}
          >
            清除 Token
          </Button>
        </Space>
      </Space>
    </div>
  );
};

export default TokenWriter;

