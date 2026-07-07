/**
 * 评测系统入口文件
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { App } from "./App";
import { LoadingProvider } from "./components/common/LoadingProvider";
import "./styles/index.css";

// 全局配置
const appConfig = {
  locale: zhCN,
  theme: {
    token: {
      colorPrimary: "#1890ff",
      borderRadius: 6,
      fontSize: 14,
    },
  },
};

// 渲染应用
const root = ReactDOM.createRoot(
  document.getElementById("evaluation-root") as HTMLElement,
);

root.render(
  <React.StrictMode>
    <ConfigProvider {...appConfig}>
      <LoadingProvider>
        <App />
      </LoadingProvider>
    </ConfigProvider>
  </React.StrictMode>,
);
