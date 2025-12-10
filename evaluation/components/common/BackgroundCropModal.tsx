import React, { useState, useRef, useCallback } from "react";
import { Modal, Button, message } from "antd";
import ReactCrop, { Crop, PixelCrop, makeAspectCrop } from "react-image-crop";
import "react-image-crop/dist/ReactCrop.css";

interface BackgroundCropModalProps {
  visible: boolean;
  imageSrc: string;
  onCancel: () => void;
  onConfirm: (croppedImageBlob: Blob) => void;
  title?: string;
}

/**
 * 背景图裁剪模态框组件
 * 支持 9:16 比例裁剪
 */
export const BackgroundCropModal: React.FC<BackgroundCropModalProps> = ({
  visible,
  imageSrc,
  onCancel,
  onConfirm,
  title = "裁剪背景图为 9:16 比例",
}) => {
  const [crop, setCrop] = useState<Crop>();
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>();
  const [localImageSrc, setLocalImageSrc] = useState<string>(imageSrc);
  const aspect = 9 / 16; // 9:16 比例
  const imgRef = useRef<HTMLImageElement>(null);

  // 使用 fetch 获取图片数据，转换为 blob URL 以避免 CORS 问题
  React.useEffect(() => {
    if (!visible || !imageSrc) return;

    let blobUrl: string | null = null;

    const loadImage = async () => {
      try {
        const response = await fetch(imageSrc, { mode: "cors" });
        if (!response.ok) {
          // 如果 CORS 失败，直接使用原始 URL
          setLocalImageSrc(imageSrc);
          return;
        }
        const blob = await response.blob();
        blobUrl = URL.createObjectURL(blob);
        setLocalImageSrc(blobUrl);
      } catch (error) {
        // 如果 fetch 失败（可能是 CORS 问题），直接使用原始 URL
        console.warn("无法通过 fetch 加载图片，使用原始 URL:", error);
        setLocalImageSrc(imageSrc);
      }
    };

    loadImage();

    // 清理函数：组件卸载或 visible 变为 false 时释放 blob URL
    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [visible, imageSrc]);

  // 初始化截取区域
  const onImageLoad = useCallback(
    (e: React.SyntheticEvent<HTMLImageElement>) => {
      const { width, height } = e.currentTarget;

      // 计算初始裁剪区域（居中，9:16 比例）
      const targetAspect = 9 / 16;
      const currentAspect = width / height;

      let cropWidth: number;
      let cropHeight: number;

      if (currentAspect > targetAspect) {
        // 图片更宽，保持高度，裁剪宽度
        cropHeight = height;
        cropWidth = height * targetAspect;
      } else {
        // 图片更高，保持宽度，裁剪高度
        cropWidth = width;
        cropHeight = width / targetAspect;
      }

      const crop = makeAspectCrop(
        {
          unit: "px",
          width: cropWidth,
          height: cropHeight,
          x: (width - cropWidth) / 2, // 水平居中
          y: (height - cropHeight) / 2, // 垂直居中
        },
        aspect,
        width,
        height,
      );
      setCrop(crop);

      // 同时设置初始的 completedCrop，这样用户不拖拽也能直接确认
      const initialCompletedCrop: PixelCrop = {
        x: (width - cropWidth) / 2,
        y: (height - cropHeight) / 2,
        width: cropWidth,
        height: cropHeight,
        unit: "px",
      };
      setCompletedCrop(initialCompletedCrop);
    },
    [aspect],
  );

  // 确认截取
  const handleConfirm = () => {
    if (!imgRef.current) {
      message.error("图片未加载");
      return;
    }

    // 如果 completedCrop 不存在，使用当前的 crop 来计算
    let finalCrop: PixelCrop;
    if (completedCrop) {
      finalCrop = completedCrop;
    } else if (crop && crop.unit === "px") {
      // 将 Crop 转换为 PixelCrop
      finalCrop = {
        x: crop.x,
        y: crop.y,
        width: crop.width,
        height: crop.height,
        unit: "px",
      };
    } else {
      message.error("请先选择截取区域");
      return;
    }

    const image = imgRef.current;
    const canvas = document.createElement("canvas");
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;

    // 计算在原始图片中的坐标
    const cropX = finalCrop.x * scaleX;
    const cropY = finalCrop.y * scaleY;
    const cropWidth = finalCrop.width * scaleX;
    const cropHeight = finalCrop.height * scaleY;

    // 设置 canvas 尺寸
    canvas.width = cropWidth;
    canvas.height = cropHeight;

    // 绘制裁剪后的图片
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      message.error("无法创建画布");
      return;
    }

    ctx.drawImage(
      image,
      cropX,
      cropY,
      cropWidth,
      cropHeight,
      0,
      0,
      cropWidth,
      cropHeight,
    );

    // 转换为 Blob
    canvas.toBlob(
      (blob) => {
        if (blob) {
          onConfirm(blob);
        } else {
          message.error("裁剪失败，请重试");
        }
      },
      "image/jpeg",
      0.95,
    );
  };

  // 重置截取区域
  const handleReset = () => {
    if (imgRef.current) {
      const { width, height } = imgRef.current;

      // 计算初始裁剪区域（居中，9:16 比例）
      const targetAspect = 9 / 16;
      const currentAspect = width / height;

      let cropWidth: number;
      let cropHeight: number;

      if (currentAspect > targetAspect) {
        cropHeight = height;
        cropWidth = height * targetAspect;
      } else {
        cropWidth = width;
        cropHeight = width / targetAspect;
      }

      const crop = makeAspectCrop(
        {
          unit: "px",
          width: cropWidth,
          height: cropHeight,
          x: (width - cropWidth) / 2,
          y: (height - cropHeight) / 2,
        },
        aspect,
        width,
        height,
      );
      setCrop(crop);

      // 同时重置 completedCrop
      const resetCompletedCrop: PixelCrop = {
        x: (width - cropWidth) / 2,
        y: (height - cropHeight) / 2,
        width: cropWidth,
        height: cropHeight,
        unit: "px",
      };
      setCompletedCrop(resetCompletedCrop);
    }
  };

  return (
    <Modal
      title={title}
      open={visible}
      onCancel={onCancel}
      width={700}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button key="reset" onClick={handleReset}>
          重置
        </Button>,
        <Button key="confirm" type="primary" onClick={handleConfirm}>
          确认裁剪
        </Button>,
      ]}
      destroyOnClose
    >
      <div style={{ textAlign: "center" }}>
        <div style={{ marginBottom: 16 }}>
          <p style={{ color: "#666", fontSize: "14px" }}>
            请拖拽调整截取区域，截取 9:16 比例的图片用于生成视频动图
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
              src={localImageSrc}
              style={{ maxWidth: "100%", maxHeight: "500px" }}
              onLoad={onImageLoad}
            />
          </ReactCrop>
        </div>
      </div>
    </Modal>
  );
};

export default BackgroundCropModal;
