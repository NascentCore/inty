/**
 * API Key 管理 Hook
 * 提供 API key 的存储、验证和管理功能
 */

import React, {
  useState,
  useEffect,
  useCallback,
  createContext,
  useContext,
} from "react";
import { message } from "antd";
import { setGlobalApiKey, updateIntyClient } from "../services/api";

interface ApiKeyContextType {
  apiKey: string | null;
  isApiKeyValid: boolean;
  isLoading: boolean;
  setApiKey: (key: string) => Promise<boolean>;
  clearApiKey: () => void;
}

const ApiKeyContext = createContext<ApiKeyContextType | null>(null);

// Cookie 管理工具
const COOKIE_NAME = "inty_api_key";
const COOKIE_EXPIRY_DAYS = 30;

const setCookie = (name: string, value: string, days: number) => {
  const expires = new Date();
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Strict`;
};

const getCookie = (name: string): string | null => {
  const nameEQ = name + "=";
  const ca = document.cookie.split(";");
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === " ") c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
  }
  return null;
};

const deleteCookie = (name: string) => {
  document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;SameSite=Strict`;
};

export const useApiKey = () => {
  const [apiKey, setApiKeyState] = useState<string | null>(null);
  const [isApiKeyValid, setIsApiKeyValid] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // 验证 API key
  const validateApiKey = useCallback(async (key: string): Promise<boolean> => {
    if (!key || key.trim() === "") {
      return false;
    }

    try {
      // 使用一个简单的 API 调用来验证 key
      const response = await fetch("/api/v1/ai/agents/me?limit=1", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${key}`,
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        return true;
      } else if (response.status === 401) {
        message.error("API Key 无效或已过期");
        return false;
      } else {
        message.error("API Key 验证失败");
        return false;
      }
    } catch (error) {
      message.error("网络错误，无法验证 API Key");
      return false;
    }
  }, []);

  // 从 cookie 加载 API key
  useEffect(() => {
    const savedApiKey = getCookie(COOKIE_NAME);
    if (savedApiKey) {
      setApiKeyState(savedApiKey);
      // 设置全局 API Key 和更新 Inty 客户端
      setGlobalApiKey(savedApiKey);
      updateIntyClient(savedApiKey);

      // 验证保存的 API key
      validateApiKey(savedApiKey).then((isValid) => {
        setIsApiKeyValid(isValid);
        setIsLoading(false);
      });
    } else {
      setIsLoading(false);
    }
  }, [validateApiKey]);

  // 设置 API key
  const setApiKey = useCallback(
    async (key: string): Promise<boolean> => {
      const trimmedKey = key.trim();
      if (!trimmedKey) {
        message.error("API Key 不能为空");
        return false;
      }

      setIsLoading(true);
      const isValid = await validateApiKey(trimmedKey);

      if (isValid) {
        setApiKeyState(trimmedKey);
        setIsApiKeyValid(true);
        setCookie(COOKIE_NAME, trimmedKey, COOKIE_EXPIRY_DAYS);

        // 更新全局 API Key 和 Inty 客户端
        setGlobalApiKey(trimmedKey);
        updateIntyClient(trimmedKey);

        message.success("API Key 设置成功");
        setIsLoading(false);
        return true;
      } else {
        setIsApiKeyValid(false);
        setIsLoading(false);
        return false;
      }
    },
    [validateApiKey],
  );

  // 清除 API key
  const clearApiKey = useCallback(() => {
    // 清除本地状态
    setApiKeyState(null);
    setIsApiKeyValid(false);

    // 清除 cookie 中的 API key
    deleteCookie(COOKIE_NAME);

    // 清除全局 API Key 并重置 Inty 客户端
    setGlobalApiKey(null);
    updateIntyClient(null);

    message.success("API Key 已清除");
  }, []);

  return {
    apiKey,
    isApiKeyValid,
    isLoading,
    setApiKey,
    clearApiKey,
  };
};

// Context Provider 组件
export const ApiKeyProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const apiKeyContext = useApiKey();

  return (
    <ApiKeyContext.Provider value={apiKeyContext}>
      {children}
    </ApiKeyContext.Provider>
  );
};

// 使用 Context 的 Hook
export const useApiKeyContext = () => {
  const context = useContext(ApiKeyContext);
  if (!context) {
    throw new Error("useApiKeyContext must be used within an ApiKeyProvider");
  }
  return context;
};
