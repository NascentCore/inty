/**
 * 工具函数统一导出
 * 从各个工具模块中导出常用函数
 */

// Storage 相关导出
export {
  storage,
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
} from "./storage";

// Device 相关导出
export {
  clearDeviceId,
  getCurrentDeviceId,
  getOrCreateDeviceId,
  regenerateDeviceId,
} from "./device";

// IntyClient 相关导出
export {
  createIntyClient,
} from "./intyClient";

// Token 相关导出
export {
  clearToken,
  getGuestToken,
  getToken,
  hasToken,
  saveToken,
} from "./token";

// Logger 相关导出
export {
  debug as logDebug,
  error as logError,
  group as logGroup,
  groupEnd as logGroupEnd,
  info as logInfo,
  test as logTest,
  testDetail as logTestDetail,
  testError as logTestError,
  testSuccess as logTestSuccess,
  warn as logWarn,
  logger,
} from "./logger";

// 错误处理相关导出
export {
  ErrorType,
  createTestErrorHandler,
  getErrorMessage,
  getErrorType,
  handleTestError,
} from "./testError";

// Agent 相关工具导出
export {
  getGenderIcon,
  getGenderText,
} from "./agentHelpers";

// 日期时间相关工具导出
export {
  formatMessageTime,
  formatDateTime,
} from "./dateHelpers";

// 侧边栏相关工具导出
export {
  formatLastMessageTime,
  truncateMessage,
  isChatActive,
} from "./sidebarHelpers";
