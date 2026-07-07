import React from "react";
import type { Agent, AvatarCropData } from "../../types";

interface BackgroundWithCropOverlayProps {
  agent: Agent;
  style?: React.CSSProperties;
  showCropOverlay?: boolean;
}

/**
 * 背景图显示组件，可选择性地显示头像截取区域的虚线框
 */
export const BackgroundWithCropOverlay: React.FC<
  BackgroundWithCropOverlayProps
> = ({ agent, style = {}, showCropOverlay = true }) => {
  const avatarCrop = agent.extensions?.avatar_crop as
    | AvatarCropData
    | undefined;

  if (!agent.background) {
    return <span style={{ color: "#999" }}>无</span>;
  }

  // 如果没有截取信息或不需要显示覆盖层，直接显示图片
  if (!avatarCrop || !showCropOverlay) {
    return <img src={agent.background} alt="background" style={style} />;
  }

  const { x, y, width, imageWidth, imageHeight } = avatarCrop;

  // 计算截取区域在显示图片中的相对位置和大小
  const cropLeft = (x / imageWidth) * 100; // 百分比
  const cropTop = (y / imageHeight) * 100; // 百分比
  const cropWidth = (width / imageWidth) * 100; // 百分比
  const cropHeight = (width / imageHeight) * 100; // 正方形，所以高度等于宽度

  return (
    <div style={{ position: "relative", display: "inline-block", ...style }}>
      {/* 背景图片 */}
      <img
        src={agent.background}
        alt="background"
        style={{
          width: "100%",
          height: "auto",
          display: "block",
        }}
      />

      {/* 截取区域覆盖层 */}
      <div
        style={{
          position: "absolute",
          left: `${cropLeft}%`,
          top: `${cropTop}%`,
          width: `${cropWidth}%`,
          height: `${cropHeight}%`,
          border: "2px dashed #ff4d4f",
          borderRadius: "50%", // 圆形虚线框
          pointerEvents: "none",
          boxSizing: "border-box",
        }}
      >
        {/* 可选的标签 */}
        <div
          style={{
            position: "absolute",
            top: "-25px",
            left: "50%",
            transform: "translateX(-50%)",
            background: "#ff4d4f",
            color: "white",
            padding: "2px 6px",
            borderRadius: "4px",
            fontSize: "10px",
            whiteSpace: "nowrap",
            pointerEvents: "none",
          }}
        >
          头像截取区域
        </div>
      </div>
    </div>
  );
};

export default BackgroundWithCropOverlay;
