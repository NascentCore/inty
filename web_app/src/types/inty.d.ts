/**
 * Inty SDK 类型声明（兼容本地 file 依赖未拉取/未生成类型的情况）
 *
 * 注意：这里只提供当前项目使用到的最小类型集合，避免影响实际 SDK 升级与完整类型覆盖。
 * - CREATED_BY_AGENT
 */

declare module 'inty' {
  export interface IIntyClientOptions {
    apiKey: string;
    baseURL?: string;
    timeout?: number;
    maxRetries?: number;
    logLevel?: string;
  }

  export class AuthenticationError extends Error {}
  export class NotFoundError extends Error {}
  export class PermissionDeniedError extends Error {}

  export default class Inty {
    constructor(options: IIntyClientOptions);

    /**
     * SDK v1 API namespace（具体结构由 SDK 生成，这里用 any 做最小兼容）
     */
    api: any;

    /**
     * SDK v2 namespace（具体结构由 SDK 生成，这里用 any 做最小兼容）
     */
    v2: any;

    static AuthenticationError: typeof AuthenticationError;
    static NotFoundError: typeof NotFoundError;
    static PermissionDeniedError: typeof PermissionDeniedError;
  }
}

