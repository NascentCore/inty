/**
 * 统一日志工具
 * 仅在开发环境输出日志，生产环境不输出
 * 用于替代直接使用 console
 */

const isDevelopment = process.env.NODE_ENV === 'development';

/**
 * 信息日志
 */
export function info(message: string, ...args: unknown[]): void {
  if (isDevelopment) {
    console.log(`[INFO] ${message}`, ...args);
  }
}

/**
 * 错误日志
 */
export function error(message: string, err?: unknown): void {
  if (isDevelopment) {
    console.error(`[ERROR] ${message}`, err);
  }
  // 生产环境可以发送到监控平台
  // TODO: 集成错误监控服务（如 Sentry）
}

/**
 * 警告日志
 */
export function warn(message: string, ...args: unknown[]): void {
  if (isDevelopment) {
    console.warn(`[WARN] ${message}`, ...args);
  }
}

/**
 * 调试日志
 */
export function debug(message: string, ...args: unknown[]): void {
  if (isDevelopment) {
    console.log(`[DEBUG] ${message}`, ...args);
  }
}

/**
 * 测试日志 - 专门用于测试组件的格式化输出
 */
export function test(title: string, data?: unknown): void {
  if (!isDevelopment) return;

  console.log(`========== ${title} ==========`);
  if (data) {
    console.log(data);
  }
}

/**
 * 测试成功日志
 */
export function testSuccess(title: string, data?: unknown): void {
  if (!isDevelopment) return;

  console.log(`✅ ${title}`, data || '');
  console.log('========================================\n');
}

/**
 * 测试失败日志
 */
export function testError(title: string, err: unknown): void {
  if (!isDevelopment) return;

  console.error(`❌ ${title}:`, err);
  console.log('========================================\n');
}

/**
 * 测试详情日志
 */
export function testDetail(label: string, value: unknown): void {
  if (!isDevelopment) return;

  console.log(`- ${label}:`, value);
}

/**
 * 分组日志开始
 */
export function group(label: string): void {
  if (isDevelopment) {
    console.group(label);
  }
}

/**
 * 分组日志结束
 */
export function groupEnd(): void {
  if (isDevelopment) {
    console.groupEnd();
  }
}

/**
 * logger 对象导出（保持向后兼容）
 */
export const logger = {
  info,
  error,
  warn,
  debug,
  test,
  testSuccess,
  testError,
  testDetail,
  group,
  groupEnd,
};

/**
 * 默认导出
 */
export default logger;
