import React from 'react';
import { Avatar } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import type { Agent } from 'inty_sdk/src/resources/api/v1/ai/agents';
import type { AvatarCropData } from '../../types';

interface AvatarDisplayProps {
  agent: Agent;
  size?: number;
  style?: React.CSSProperties;
  showBackground?: boolean; // 是否显示半透明背景图
}

/**
 * 头像显示组件
 * 根据坐标信息动态显示截取的头像区域
 */
export const AvatarDisplay: React.FC<AvatarDisplayProps> = ({
  agent,
  size = 64,
  style = {},
  showBackground = false
}) => {
  // 如果有头像坐标信息，使用截取方式显示
  const avatarCrop = agent.extensions?.avatar_crop as AvatarCropData | undefined;
  
  if (avatarCrop && agent.background) {
    const { x, y, width, imageWidth, imageHeight } = avatarCrop;
    const sourceImageUrl = agent.background;

    // 计算缩放比例 - 让截取区域填满整个容器
    // 截取区域是正方形，所以直接用宽度计算缩放
    const scale = size / width;
    
    // 计算图片在容器中的位置
    // 对于截取显示，我们应该显示整个原始图片，然后通过定位来显示截取区域
    const imageDisplayWidth = imageWidth * scale;
    const imageDisplayHeight = imageHeight * scale;
    const offsetX = -x * scale;
    const offsetY = -y * scale;

    
    return (
      <div
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          overflow: 'hidden',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          ...style
        }}
      >
        {/* 半透明背景图 - 显示完整原始图片 */}
        {showBackground && (
          <img
            src={sourceImageUrl}
            alt="Background"
            style={{
              width: '100%',
              height: '100%',
              position: 'absolute',
              left: 0,
              top: 0,
              objectFit: 'cover',
              opacity: 0.3,
              zIndex: 1
            }}
          />
        )}
        {/* 截取的头像区域 - 只显示截取部分 */}
        <img
          src={sourceImageUrl}
          alt="Avatar"
          style={{
            width: imageDisplayWidth,
            height: imageDisplayHeight,
            position: 'absolute',
            left: offsetX,
            top: offsetY,
            objectFit: 'cover',
            zIndex: 2
          }}
        />
      </div>
    );
  }
  
  // 如果没有坐标信息，使用传统头像显示方式
  
  return (
    <Avatar
      size={size}
      src={agent.avatar}
      icon={<RobotOutlined />}
      style={style}
    />
  );
};

export default AvatarDisplay;
