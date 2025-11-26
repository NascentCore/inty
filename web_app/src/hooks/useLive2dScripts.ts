/**
 * useLive2dScripts
 *
 * 用途：动态注入 Live2D Cubism Core 所需脚本，确保在渲染 Live2D 模型之前完成加载。
 *
 * 使用示例：
 * ```ts
 * const scriptsReady = useLive2dScripts();
 * if (!scriptsReady) {
 *   return <Spinner />;
 * }
 * ```
 *
 * 注意事项：
 * - 默认指向官方 CDN，可在后续根据部署环境替换为自有 CDN。
 * - 仅负责注入脚本，不创建 PIXI 实例。
 */
import { useEffect, useState } from 'react';

const CORE_SCRIPTS = [
  'https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js',
];

const hasScriptTag = (src: string): boolean =>
  !!document.querySelector(`script[src="${src}"]`);

export const useLive2dScripts = (): boolean => {
  const [loaded, setLoaded] = useState<boolean>(
    typeof window !== 'undefined' && Boolean((window as any).Live2DCubismCore),
  );

  useEffect(() => {
    if (loaded) {
      return;
    }
    let isMounted = true;

    const loadScript = (src: string): Promise<void> => {
      if (hasScriptTag(src)) {
        return Promise.resolve();
      }
      return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`Failed to load ${src}`));
        document.body.appendChild(script);
      });
    };

    Promise.all(CORE_SCRIPTS.map(loadScript))
      .then(() => {
        if (!isMounted) {
          return;
        }
        // 等待全局变量挂载
        requestAnimationFrame(() => setLoaded(true));
      })
      .catch((error) => {
        console.error('[useLive2dScripts] load error:', error);
      });

    return () => {
      isMounted = false;
    };
  }, [loaded]);

  return loaded;
};


