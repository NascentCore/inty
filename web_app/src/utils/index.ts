/**
 * 工具函数统一导出
 * 从各个工具模块中导出常用函数
 */

// Agent 相关工具导出
export { getGenderIcon, getGenderText } from './agentHelpers';
// 日期时间相关工具导出
export { formatDateTime, formatMessageTime } from './dateHelpers';
// Device 相关导出
export {
  clearDeviceId,
  getCurrentDeviceId,
  getOrCreateDeviceId,
  regenerateDeviceId,
} from './device';
// IntyClient 相关导出
export { createIntyClient } from './intyClient';

// Logger 相关导出
export {
  debug as logDebug,
  error as logError,
  group as logGroup,
  groupEnd as logGroupEnd,
  info as logInfo,
  logger,
  test as logTest,
  testDetail as logTestDetail,
  testError as logTestError,
  testSuccess as logTestSuccess,
  warn as logWarn,
} from './logger';
// 侧边栏相关工具导出
export { formatLastMessageTime, isChatActive, truncateMessage } from './sidebarHelpers';
// Storage 相关导出
export {
  clear as storageClear,
  default as storageDefault,
  driver as storageDriver,
  get as storageGet,
  getMultiple as storageGetMultiple,
  has as storageHas,
  iterate as storageIterate,
  keys as storageKeys,
  length as storageLength,
  remove as storageRemove,
  removeMultiple as storageRemoveMultiple,
  set as storageSet,
  setMultiple as storageSetMultiple,
  storage,
} from './storage';
// 错误处理相关导出
export {
  createTestErrorHandler,
  ErrorType,
  getErrorMessage,
  getErrorType,
  handleTestError,
} from './testError';
// Token 相关导出
export { clearToken, getToken, hasToken, saveToken } from './token';
