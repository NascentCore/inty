import { UploadOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';
import { Button, message, Space, Upload } from 'antd';
import React, { useState } from 'react';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 上传图片测试组件
 */
const UploadImage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const handleTest = async () => {
    if (fileList.length === 0) {
      message.error('请先选择图片文件');
      return;
    }

    setLoading(true);
    logger.test('上传图片');

    try {
      const file = fileList[0].originFileObj as File;

      logger.testDetail('文件名', file.name);
      logger.testDetail('文件大小', `${(file.size / 1024).toFixed(2)} KB`);
      logger.testDetail('文件类型', file.type);

      const client = await createIntyClient(true);
      const response = await client.api.v1.uploadImage({
        file,
      });

      // 自定义成功日志
      if (response.data) {
        logger.testDetail('图片URL', response.data.url);
      }

      logger.testSuccess('上传图片', response);
      message.success('上传成功');
    } catch (err: unknown) {
      logger.testError('上传图片', err);
      message.error('上传失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="test-component">
      <h4>上传图片</h4>
      <p className="test-tip">上传图片文件，支持验证、压缩和云存储</p>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div>
          <div style={{ marginBottom: 4 }}>选择图片文件:</div>
          <Upload
            beforeUpload={() => false}
            fileList={fileList}
            onChange={({ fileList }) => setFileList(fileList)}
            maxCount={1}
            accept="image/*"
          >
            <Button icon={<UploadOutlined />} style={{ width: '100%', marginTop: 8 }}>
              选择图片
            </Button>
          </Upload>
        </div>

        <Button type="primary" onClick={handleTest} loading={loading} block>
          执行测试
        </Button>
      </Space>
    </div>
  );
};

export default UploadImage;
