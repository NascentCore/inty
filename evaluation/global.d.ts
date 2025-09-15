// 全局类型声明
declare global {
  interface Window {
    hideLoading?: () => void;
  }

  // 环境变量
  const REACT_APP_API_BASE_URL: string;
  const INTY_BASE_URL: string;
  const INTY_API_KEY: string;
}

// Vite 环境变量类型
interface ImportMetaEnv {
  readonly VITE_REACT_APP_API_BASE_URL: string;
  readonly VITE_INTY_BASE_URL: string;
  readonly VITE_INTY_API_KEY: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

export {};
