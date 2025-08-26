import { useState, useCallback } from "react";

interface UseJsonDisplayReturn {
  jsonModalVisible: boolean;
  jsonData: string;
  showJson: (data: any) => void;
  hideJson: () => void;
}

export const useJsonDisplay = (): UseJsonDisplayReturn => {
  const [jsonModalVisible, setJsonModalVisible] = useState(false);
  const [jsonData, setJsonData] = useState("");

  const showJson = useCallback((data: any) => {
    try {
      const formattedJson = JSON.stringify(data, null, 2);
      setJsonData(formattedJson);
      setJsonModalVisible(true);
    } catch (error) {
      console.error("准备JSON数据失败:", error);
    }
  }, []);

  const hideJson = useCallback(() => {
    setJsonModalVisible(false);
    setJsonData("");
  }, []);

  return {
    jsonModalVisible,
    jsonData,
    showJson,
    hideJson,
  };
};
