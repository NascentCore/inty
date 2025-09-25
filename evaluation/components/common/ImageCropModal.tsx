import React, { useState, useRef, useCallback } from "react";
import { Modal, Button, message } from "antd";
import ReactCrop, { Crop, PixelCrop, makeAspectCrop } from "react-image-crop";
import "react-image-crop/dist/ReactCrop.css";
import type { AvatarCropData } from "../../types";

/**
 * 将 AvatarCropData 转换为 ReactCrop 的 Crop 对象
 * @param existingCropData 现有的裁剪数据
 * @param displayWidth 显示区域的宽度
 * @param displayHeight 显示区域的高度
 * @param aspect 宽高比，默认为1（正方形）
 * @returns ReactCrop 的 Crop 对象
 */
const createCropFromAvatarData = (
  existingCropData: AvatarCropData,
  displayWidth: number,
  displayHeight: number,
  aspect: number = 1,
): Crop => {
  const {
    x,
    y,
    width: cropWidth,
    height: cropHeight,
    imageWidth,
    imageHeight,
  } = existingCropData;

  // 计算缩放比例
  const scaleX = displayWidth / imageWidth;
  const scaleY = displayHeight / imageHeight;

  // 将原始坐标转换为显示坐标
  const displayX = x * scaleX;
  const displayY = y * scaleY;
  const scaledWidth = cropWidth * scaleX;
  const scaledHeight = cropHeight * scaleY;

  return makeAspectCrop(
    {
      unit: "px",
      width: scaledWidth,
      height: scaledHeight,
      x: displayX,
      y: displayY,
    },
    aspect,
    displayWidth,
    displayHeight,
  );
};

interface ImageCropModalProps {
  visible: boolean;
  imageSrc: string;
  onCancel: () => void;
  onConfirm: (cropData: AvatarCropData) => void;
  title?: string;
  existingCropData?: AvatarCropData; // 现有的裁剪数据，用于初始化裁剪区域
}

/**
 * 图片截取模态框组件
 * 支持正方形截取
 */
export const ImageCropModal: React.FC<ImageCropModalProps> = ({
  visible,
  imageSrc,
  onCancel,
  onConfirm,
  title = "截取头像",
  existingCropData,
}) => {
  const [crop, setCrop] = useState<Crop>();
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>();
  const [aspect] = useState<number | undefined>(1); // 1:1 正方形比例
  const imgRef = useRef<HTMLImageElement>(null);

  // 初始化截取区域
  const onImageLoad = useCallback(
    (e: React.SyntheticEvent<HTMLImageElement>) => {
      const { width, height } = e.currentTarget;

      // 如果有现有的裁剪数据，使用它来初始化裁剪区域
      if (existingCropData) {
        const crop = createCropFromAvatarData(
          existingCropData,
          width,
          height,
          1,
        );
        setCrop(crop);
      } else {
        // 默认行为：计算截取区域的宽度（与图片等宽）
        const cropWidth = width;
        const cropHeight = width; // 正方形，所以高度等于宽度

        // 如果图片高度小于宽度，则使用图片高度作为截取区域大小
        const finalCropSize = Math.min(cropWidth, cropHeight, height);

        const crop = makeAspectCrop(
          {
            unit: "px",
            width: finalCropSize,
            height: finalCropSize,
            x: (width - finalCropSize) / 2, // 水平居中
            y: 0, // 顶部对齐
          },
          1,
          width,
          height,
        );
        setCrop(crop);
      }
    },
    [existingCropData],
  );

  // 确认截取
  const handleConfirm = () => {
    if (!completedCrop || !imgRef.current) {
      message.error("请先选择截取区域");
      return;
    }

    const image = imgRef.current;
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;

    // 计算在原始图片中的坐标
    const cropData: AvatarCropData = {
      x: Math.round(completedCrop.x * scaleX),
      y: Math.round(completedCrop.y * scaleY),
      width: Math.round(completedCrop.width * scaleX),
      height: Math.round(completedCrop.height * scaleY),
      imageWidth: image.naturalWidth,
      imageHeight: image.naturalHeight,
    };

    onConfirm(cropData);
    message.success("头像坐标设置成功");
  };

  // 重置截取区域
  const handleReset = () => {
    if (imgRef.current) {
      const { width, height } = imgRef.current;

      // 如果有现有的裁剪数据，重置到该位置
      if (existingCropData) {
        const crop = createCropFromAvatarData(
          existingCropData,
          width,
          height,
          1,
        );
        setCrop(crop);
      } else {
        // 默认行为：计算截取区域的宽度（与图片等宽）
        const cropWidth = width;
        const cropHeight = width; // 正方形，所以高度等于宽度

        // 如果图片高度小于宽度，则使用图片高度作为截取区域大小
        const finalCropSize = Math.min(cropWidth, cropHeight, height);

        const crop = makeAspectCrop(
          {
            unit: "px",
            width: finalCropSize,
            height: finalCropSize,
            x: (width - finalCropSize) / 2, // 水平居中
            y: 0, // 顶部对齐
          },
          1,
          width,
          height,
        );
        setCrop(crop);
      }
    }
  };

  return (
    <Modal
      title={title}
      open={visible}
      onCancel={onCancel}
      width={600}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button key="reset" onClick={handleReset}>
          重置
        </Button>,
        <Button key="confirm" type="primary" onClick={handleConfirm}>
          确认截取
        </Button>,
      ]}
      destroyOnClose
    >
      <div style={{ textAlign: "center" }}>
        <div style={{ marginBottom: 16 }}>
          <p style={{ color: "#666", fontSize: "14px" }}>
            请拖拽调整截取区域，截取正方形图片作为头像
          </p>
        </div>

        <div style={{ marginBottom: 16 }}>
          <ReactCrop
            crop={crop}
            onChange={(_, percentCrop) => setCrop(percentCrop)}
            onComplete={(c) => setCompletedCrop(c)}
            aspect={aspect}
            minWidth={50}
            minHeight={50}
          >
            <img
              ref={imgRef}
              alt="Crop me"
              src={imageSrc}
              style={{ maxWidth: "100%", maxHeight: "400px" }}
              onLoad={onImageLoad}
            />
          </ReactCrop>
        </div>
      </div>
    </Modal>
  );
};

export default ImageCropModal;
