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
const MOUTH_VALUE_VERIFY_INTERVAL_MS = 1000;
const LIVE2D_DEBUG_LIP_SYNC_STORAGE_KEY = 'INTY_DEVTEST_LIVE2D_DEBUG_LIP_SYNC';
const LIVE2D_DEBUG_LIP_SYNC_QUERY_KEY = 'live2dDebugLipSync';

const getLive2dDebugLipSyncEnabled = (): boolean => {
  if (typeof window === 'undefined') {
    return false;
  }
  try {
    const url = new URL(window.location.href);
    const queryValue = url.searchParams.get(LIVE2D_DEBUG_LIP_SYNC_QUERY_KEY);
    if (queryValue === '1' || queryValue === 'true') {
      return true;
    }
    if (queryValue === '0' || queryValue === 'false') {
      return false;
    }
  } catch {
    // ignore
  }
  try {
    return window.localStorage.getItem(LIVE2D_DEBUG_LIP_SYNC_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
};

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
    const updateMouthRef = useRef<(() => void) | null>(null);
    const lastLogTimeRef = useRef<number>(0);
    const internalModelEventTargetRef = useRef<any>(null);
    const internalModelBeforeModelUpdateListenerRef = useRef<(() => void) | null>(null);
    const mouthValueLastVerifyTimeRef = useRef<number>(0);
    const lipSyncViaInternalModelRef = useRef<boolean>(false);

    useEffect(() => {
      onReadyRef.current = onReady;
    }, [onReady]);

    const debugLipSyncEnabledRef = useRef<boolean>(getLive2dDebugLipSyncEnabled());

    const setMouthValue = (value: number) => {
      const coreModel = modelRef.current?.internalModel?.coreModel as
        | ILive2DCoreModel
        | undefined;
      if (!coreModel) {
        console.warn('[Live2DViewer] setMouthValue: coreModel not available');
        return;
      }
      try {
        coreModel.setParameterValueById(MOUTH_PARAM_ID, value);
        // 调试校验：读回参数值，确认没有被覆盖（节流 + 默认关闭）
        if (debugLipSyncEnabledRef.current) {
          const now = Date.now();
          if (now - mouthValueLastVerifyTimeRef.current > MOUTH_VALUE_VERIFY_INTERVAL_MS) {
            mouthValueLastVerifyTimeRef.current = now;
            const actualValue = coreModel.getParameterValueById(MOUTH_PARAM_ID);
            if (Math.abs(actualValue - value) > 0.001) {
              console.warn(
                `[Live2DViewer] setMouthValue: value mismatch`,
                `expected=${value.toFixed(3)}, actual=${actualValue.toFixed(3)}`,
              );
            }
          }
        }
      } catch (err) {
        console.warn('[Live2DViewer] setMouthValue: failed to set parameter', MOUTH_PARAM_ID, err);
      }
    };

    // 计算并设置当前应该的嘴型值（根据是否正在说话）
    const updateMouthValue = () => {
      if (!modelRef.current) {
        return;
      }
      const now = Date.now();
      const isTalking = now < talkingEndTimeRef.current;

      if (isTalking) {
        const wave =
          (Math.sin(now / 90) + Math.sin(now / 45) + Math.sin(now / 30)) / 3;
        const normalized = Math.min(1, Math.max(0, (wave + 1) / 2));
        setMouthValue(normalized * 0.85);
      } else {
        setMouthValue(0);
      }
    };

    const updateMouth = () => {
      if (!modelRef.current) {
        return;
      }
      const now = Date.now();
      const isTalking = now < talkingEndTimeRef.current;

      // 节流日志：如果正在说话，每 2 秒记录一次（避免刷屏）
      if (isTalking && now - lastLogTimeRef.current > 2000) {
        lastLogTimeRef.current = now;
        const wave =
          (Math.sin(now / 90) + Math.sin(now / 45) + Math.sin(now / 30)) / 3;
        const normalized = Math.min(1, Math.max(0, (wave + 1) / 2));
        const mouthValue = normalized * 0.85;
        console.debug(
          '[Live2DViewer] updateMouth: talking',
          `now=${now}, endTime=${talkingEndTimeRef.current}, remaining=${talkingEndTimeRef.current - now}ms`,
          `mouthValue=${mouthValue.toFixed(3)}`,
        );
      }

      // 如果 beforeModelUpdate 已接管嘴型更新，这里就不重复写参数，避免额外开销
      if (!lipSyncViaInternalModelRef.current) {
        updateMouthValue();
      }
    };

    const destroyModel = () => {
      const model = modelRef.current;
      if (!model) {
        return;
      }
      try {
        // 移除 internalModel 事件监听，避免热更新 / 重载导致重复绑定
        if (internalModelEventTargetRef.current && internalModelBeforeModelUpdateListenerRef.current) {
          const target = internalModelEventTargetRef.current;
          const handler = internalModelBeforeModelUpdateListenerRef.current;
          try {
            if (typeof target.off === 'function') {
              target.off('beforeModelUpdate', handler);
            } else if (typeof target.removeListener === 'function') {
              target.removeListener('beforeModelUpdate', handler);
            }
          } finally {
            internalModelEventTargetRef.current = null;
            internalModelBeforeModelUpdateListenerRef.current = null;
            lipSyncViaInternalModelRef.current = false;
          }
        }

        // 移除嘴型动画 ticker
        if (appRef.current && updateMouthRef.current) {
          appRef.current.ticker.remove(updateMouthRef.current);
          updateMouthRef.current = null;
        }
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
            console.warn('[Live2DViewer] speakText: empty text provided');
            return;
          }
          const duration = text.length * TALKING_COEFFICIENT + TALKING_BUFFER;
          const endTime = Date.now() + duration;
          talkingEndTimeRef.current = endTime;
          console.log(
            '[Live2DViewer] speakText: triggered',
            `textLength=${text.length}, duration=${duration}ms, endTime=${endTime}`,
          );
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
            }
          });

          // 监听 motionStart 事件，更新当前动作状态并打印日志
          // 注意：事件由 motionManager 发射，而非 model 本身
          const motionManager = model.internalModel.motionManager;
          if (motionManager) {
            console.log('[Live2DViewer] MotionManager found, attaching listeners');
            (motionManager as any).on(
              'motionStart',
              (group: string, index: number, audio?: any) => {
                console.log(
                  `[Live2DViewer] motionStart: group=${group} index=${index}`,
                  audio ? '(has audio)' : '',
                );
                currentMotionRef.current = {
                  group,
                  index,
                  timestamp: Date.now(),
                };
              },
            );
          } else {
            console.warn(
              '[Live2DViewer] motionManager not found, cannot listen to motionStart events',
            );
          }

          // 方案 A：监听 internalModel 的 beforeModelUpdate，在参数最终应用前重新写嘴型
          // 事件属于 InternalModelEvents（由 internalModel 发射），比挂在 motionManager 上更可靠
          const internalModel = model.internalModel as any;
          if (internalModel && typeof internalModel.on === 'function') {
            // 若之前有残留监听（例如热更新），先尝试解绑
            if (internalModelEventTargetRef.current && internalModelBeforeModelUpdateListenerRef.current) {
              const prevTarget = internalModelEventTargetRef.current;
              const prevHandler = internalModelBeforeModelUpdateListenerRef.current;
              try {
                if (typeof prevTarget.off === 'function') {
                  prevTarget.off('beforeModelUpdate', prevHandler);
                } else if (typeof prevTarget.removeListener === 'function') {
                  prevTarget.removeListener('beforeModelUpdate', prevHandler);
                }
              } catch {
                // 忽略解绑失败
              } finally {
                internalModelEventTargetRef.current = null;
                internalModelBeforeModelUpdateListenerRef.current = null;
              }
            }

            const beforeModelUpdateHandler = () => {
              updateMouthValue();
            };
            internalModelEventTargetRef.current = internalModel;
            internalModelBeforeModelUpdateListenerRef.current = beforeModelUpdateHandler;
            internalModel.on('beforeModelUpdate', beforeModelUpdateHandler);
            lipSyncViaInternalModelRef.current = true;
            console.log('[Live2DViewer] beforeModelUpdate listener attached (lip sync override)');
          } else {
            console.warn('[Live2DViewer] internalModel does not support events; cannot attach beforeModelUpdate');
          }

          app.stage.addChild(model);
          modelRef.current = model;
          currentMotionRef.current = null;
          // 在模型加载完成后添加嘴型动画 ticker
          if (app.ticker && !updateMouthRef.current) {
            updateMouthRef.current = updateMouth;
            app.ticker.add(updateMouth);
            console.log('[Live2DViewer] Mouth animation ticker added successfully');

            // 验证嘴型参数是否存在（通过尝试读取参数值来验证）
            const coreModel = model.internalModel?.coreModel as ILive2DCoreModel | undefined;
            if (coreModel) {
              try {
                // 尝试读取参数值来验证参数是否存在
                const testValue = coreModel.getParameterValueById(MOUTH_PARAM_ID);
                console.log(
                  `[Live2DViewer] Mouth parameter "${MOUTH_PARAM_ID}" verified`,
                  `current value=${testValue.toFixed(3)}`,
                );
              } catch (err) {
                console.warn(
                  `[Live2DViewer] Mouth parameter "${MOUTH_PARAM_ID}" not found or not accessible:`,
                  err,
                );
                // 尝试通过 parameters.ids 查找（如果可用）
                try {
                  const params = (coreModel as any).parameters;
                  if (params && Array.isArray(params.ids)) {
                    const found = params.ids.includes(MOUTH_PARAM_ID);
                    console.warn(
                      `[Live2DViewer] Parameter check via parameters.ids:`,
                      found ? 'found' : 'not found',
                      `(total: ${params.ids.length})`,
                    );
                  }
                } catch (e) {
                  // 忽略，parameters 可能不可用
                }
              }
            } else {
              console.warn('[Live2DViewer] coreModel not available for parameter verification');
            }
          } else {
            if (!app.ticker) {
              console.warn('[Live2DViewer] Cannot add mouth ticker: app.ticker is not available');
            }
            if (updateMouthRef.current) {
              console.warn('[Live2DViewer] Mouth ticker already exists, skipping');
            }
          }
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


