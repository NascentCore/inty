import React from "react";
import { Avatar } from "antd";
import { RobotOutlined } from "@ant-design/icons";
import type { Agent, AvatarCropData } from "../../types";

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
  showBackground = false,
}) => {
  const avatarCrop = agent.extensions?.avatar_crop as
    | AvatarCropData
    | undefined;

  // 1. 优先使用 avatar_crop + background
  if (avatarCrop && agent.background) {
    const { x, y, width, imageWidth, imageHeight } = avatarCrop;
    const sourceImageUrl = agent.background;

    // 计算缩放比例 - 让截取区域填满整个容器
    const scale = size / width;

    // 计算图片在容器中的位置
    const imageDisplayWidth = imageWidth * scale;
    const imageDisplayHeight = imageHeight * scale;
    const offsetX = -x * scale;
    const offsetY = -y * scale;

    return (
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          overflow: "hidden",
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          margin: "0 auto",
          ...style,
        }}
      >
        {/* 半透明背景图 - 显示完整原始图片 */}
        {showBackground && (
          <img
            src={sourceImageUrl}
            alt="Background"
            style={{
              width: "100%",
              height: "100%",
              position: "absolute",
              left: 0,
              top: 0,
              objectFit: "cover",
              opacity: 0.3,
              zIndex: 1,
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
            position: "absolute",
            left: offsetX,
            top: offsetY,
            objectFit: "cover",
            zIndex: 2,
          }}
        />
      </div>
    );
  }

  // 2. 如果没有坐标信息，检查 agent.avatar
  if (agent.avatar) {
    return (
      <Avatar
        size={size}
        src={agent.avatar}
        icon={<RobotOutlined />}
        style={style}
      />
    );
  }

  // 3. 最后使用 agent.background 顶部居中对齐截取正方形
  if (agent.background) {
    return (
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          overflow: "hidden",
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          margin: "0 auto",
          ...style,
        }}
      >
        <img
          src={agent.background}
          alt="Avatar"
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "center top",
          }}
        />
      </div>
    );
  }

  // 如果都没有，显示默认图标
  return <Avatar size={size} icon={<RobotOutlined />} style={style} />;
};

export default AvatarDisplay;
