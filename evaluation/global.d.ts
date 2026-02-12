// 全局类型声明
declare global {
  interface Window {
    hideLoading?: () => void;
  }
}

declare module "inty" {
  export class Inty {
    constructor(config: { baseURL: string; apiKey: string });
    api: any;
  }
}

export {};
