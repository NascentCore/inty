/**
 * Live2DViewer
 *
 * 用途：封装 pixi-live2d-display，提供在 React 中加载 Live2D 模型的能力，
 * 并支持基于文本长度模拟嘴型动画（Milestone A）。
 *
 * 使用示例：
 * ```tsx
 * const viewerRef = useRef<ILive2DViewerRef>(null);
 *
 * <Live2DViewer
 *   ref={viewerRef}
 *   modelUrl="/live2d-models/haru/Haru.model3.json"
 *   scale={0.2}
 * />
 *
 * viewerRef.current?.speakText('Hello world');
 * ```
 *
 * Props 说明：
 * - modelUrl: string - `.model3.json` 的完整 URL
 * - scale?: number - 缩放倍数
 * - x?: number - 模型 X 坐标
 * - y?: number - 模型 Y 坐标
 * - onReady?: () => void - 模型加载完成回调
 *
 * 注意事项：
 * - 依赖 pixi.js v7 与 pixi-live2d-display，需先安装依赖
 * - Live2D 核心脚本通过 useLive2dScripts 动态注入
 */
import React, {
  ForwardedRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';
import * as PIXI from 'pixi.js';
import type { Live2DModel as ILive2DModel } from 'pixi-live2d-display/cubism4';

import { useLive2dScripts } from '@/hooks/useLive2dScripts';

import './index.less';

// 将 PIXI 暴露给全局，供 pixi-live2d-display 使用
(window as any).PIXI = (window as any).PIXI || PIXI;

type Live2DModelCtor = typeof import('pixi-live2d-display/cubism4')['Live2DModel'];

let live2DModelInstance: Live2DModelCtor | null = null;
let live2DModelPromise: Promise<Live2DModelCtor> | null = null;

const loadLive2DModel = async (): Promise<Live2DModelCtor> => {
  if (live2DModelInstance) {
    return live2DModelInstance;
  }
  if (!live2DModelPromise) {
    live2DModelPromise = import('pixi-live2d-display/cubism4')
      .then((module) => {
        const Model = module.Live2DModel;
        Model.registerTicker(PIXI.Ticker);
        live2DModelInstance = Model;
        return Model;
      })
      .finally(() => {
        live2DModelPromise = null;
      });
  }
  return live2DModelPromise;
};

const DEFAULT_SCALE = 0.18;
const TALKING_COEFFICIENT = 150;
const TALKING_BUFFER = 500;
const MOUTH_PARAM_ID = 'ParamMouthOpenY';

interface ILive2DCoreModel {
  setParameterValueById: (parameterId: string, value: number) => void;
  getParameterValueById: (parameterId: string) => number;
  getParameterCount: () => number;
  getParameterId: (index: number) => string;
}

interface ICurrentMotionInfo {
  group: string | null;
  index: number | null;
  timestamp: number;
}

export interface ILive2DViewerRef {
  speakText: (text: string) => void;
  stopSpeaking: () => void;
  motion: (group: string, index?: number) => void;
  internalModel: ILive2DModel | null;
  getCurrentMotion: () => ICurrentMotionInfo | null;
  getParameterValue: (parameterId: string) => number | null;
  getAllParameters: () => Array<{ id: string; value: number }> | null;
}

interface ILive2DViewerProps {
  modelUrl: string;
  scale?: number;
  x?: number;
  y?: number;
  onReady?: () => void;
}

const createPixiApp = (canvas: HTMLCanvasElement): PIXI.Application => {
  return new PIXI.Application({
    view: canvas,
    autoStart: true,
    backgroundAlpha: 0,
    resizeTo: canvas.parentElement ?? window,
  });
};

const Live2DViewer = React.forwardRef(
  (
    { modelUrl, scale = DEFAULT_SCALE, x = 0, y = 0, onReady }: ILive2DViewerProps,
    ref: ForwardedRef<ILive2DViewerRef>,
  ) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const appRef = useRef<PIXI.Application | null>(null);
    const modelRef = useRef<ILive2DModel | null>(null);
    const talkingEndTimeRef = useRef<number>(0);
    const scriptsReady = useLive2dScripts();
    const [error, setError] = useState<string | null>(null);
    const onReadyRef = useRef<(() => void) | undefined>(onReady);
    const currentMotionRef = useRef<ICurrentMotionInfo | null>(null);

    useEffect(() => {
      onReadyRef.current = onReady;
    }, [onReady]);

    const setMouthValue = (value: number) => {
      const coreModel = modelRef.current?.internalModel?.coreModel as
        | ILive2DCoreModel
        | undefined;
      if (!coreModel) {
        return;
      }
      coreModel.setParameterValueById(MOUTH_PARAM_ID, value);
    };

    const destroyModel = () => {
      const model = modelRef.current;
      if (!model) {
        return;
      }
      try {
        // 如果 App 还存在且模型还在 stage 中，先移除
        if (appRef.current?.stage && model.parent) {
          appRef.current.stage.removeChild(model);
        }
        // 安全销毁模型
        if (model.destroy) {
          model.destroy();
        }
      } catch (err) {
        // 模型可能已经被部分销毁，忽略错误
        console.warn('[Live2DViewer] Error destroying model (may already be destroyed):', err);
      } finally {
        modelRef.current = null;
      }
    };

    useImperativeHandle(
      ref,
      () => ({
        speakText: (text: string) => {
          if (!text) {
            return;
          }
          const duration = text.length * TALKING_COEFFICIENT + TALKING_BUFFER;
          talkingEndTimeRef.current = Date.now() + duration;
        },
        stopSpeaking: () => {
          talkingEndTimeRef.current = 0;
          setMouthValue(0);
        },
        motion: (group: string, index?: number) => {
          if (!group || !modelRef.current) {
            return;
          }
          modelRef.current.motion(group, index);
          currentMotionRef.current = {
            group,
            index: index ?? 0,
            timestamp: Date.now(),
          };
        },
        get internalModel() {
          return modelRef.current;
        },
        getCurrentMotion: () => currentMotionRef.current,
        getParameterValue: (parameterId: string) => {
          const coreModel = modelRef.current?.internalModel?.coreModel as
            | ILive2DCoreModel
            | undefined;
          if (!coreModel) {
            return null;
          }
          try {
            return coreModel.getParameterValueById(parameterId);
          } catch {
            return null;
          }
        },
        getAllParameters: () => {
          const coreModel = modelRef.current?.internalModel?.coreModel as
            | ILive2DCoreModel
            | undefined;
          if (!coreModel) {
            return null;
          }
          try {
            const count = coreModel.getParameterCount();
            return Array.from({ length: count }, (_, index) => {
              const id = coreModel.getParameterId(index);
              const value = coreModel.getParameterValueById(id);
              return { id, value };
            });
          } catch {
            return null;
          }
        },
      }),
      [],
    );

    // 初始化 PIXI Application
    useEffect(() => {
      if (!scriptsReady || !canvasRef.current || appRef.current) {
        return;
      }
      const app = createPixiApp(canvasRef.current);
      appRef.current = app;

      return () => {
        // 先手动清理模型，避免 App 销毁时自动清理导致的问题
        destroyModel();
        // 然后销毁 App
        app.destroy(true, { children: true, texture: true });
        appRef.current = null;
      };
    }, [scriptsReady]);

    // 加载 Live2D 模型
    useEffect(() => {
      if (!appRef.current || !modelUrl || !scriptsReady) {
        return;
      }
      let isMounted = true;
      const app = appRef.current;

      const loadModel = async () => {
        setError(null);
        destroyModel();
        try {
          const Live2DModel = await loadLive2DModel();
          const model = await Live2DModel.from(modelUrl);
          if (!isMounted) {
            model.destroy();
            return;
          }
          model.scale.set(scale);
          model.x = x;
          model.y = y;
          model.interactive = true;
          model.on('hit', (hitAreas: string[]) => {
            if (hitAreas.includes('body')) {
              model.motion('TapBody');
              currentMotionRef.current = {
                group: 'TapBody',
                index: 0,
                timestamp: Date.now(),
              };
            }
          });
          app.stage.addChild(model);
          modelRef.current = model;
          currentMotionRef.current = null;
          onReadyRef.current?.();
        } catch (err) {
          console.error('[Live2DViewer] failed to load model:', err);
          setError('Failed to load Live2D model, please check the console output.');
        }
      };

      loadModel();

      return () => {
        isMounted = false;
        destroyModel();
      };
    }, [modelUrl, scale, x, y, scriptsReady]);

    // 嘴型模拟 Ticker
    useEffect(() => {
      if (!appRef.current) {
        return;
      }
      const updateMouth = () => {
        if (!modelRef.current) {
          return;
        }
        const now = Date.now();
        if (now < talkingEndTimeRef.current) {
          const wave =
            (Math.sin(now / 90) + Math.sin(now / 45) + Math.sin(now / 30)) / 3;
          const normalized = Math.min(1, Math.max(0, (wave + 1) / 2));
          setMouthValue(normalized * 0.85);
        } else {
          setMouthValue(0);
        }
      };
      appRef.current.ticker.add(updateMouth);
      return () => {
        appRef.current?.ticker.remove(updateMouth);
      };
    }, []);

    return (
      <div className="live2d-viewer">
        {!scriptsReady ? (
          <div className="live2d-viewer__loading">Loading Live2D core scripts...</div>
        ) : null}
        {error ? <div className="live2d-viewer__error">{error}</div> : null}
        <canvas ref={canvasRef} className="live2d-viewer__canvas" />
      </div>
    );
  },
);

Live2DViewer.displayName = 'Live2DViewer';

export default Live2DViewer;


