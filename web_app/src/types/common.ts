/**
 * 通用公共类型定义
 */

/**
 * 菜单项接口
 */
export interface IMenuItem {
  /** 路由路径 */
  path: string;
  /** 菜单显示标签 */
  label: string;
  /** 菜单图标（可以是 emoji 或图标组件） */
  icon?: string | React.ReactNode;
  /** 是否在菜单中隐藏 */
  hideInMenu?: boolean;
  /** 子菜单项 */
  children?: IMenuItem[];
}

/**
 * 应用初始状态接口
 */
export interface IInitialState {
  /** 应用名称 */
  name?: string;
}

/**
 * 路由配置接口
 */
export interface IRouteConfig {
  /** 路由路径 */
  path: string;
  /** 组件路径 */
  component?: string;
  /** 路由名称 */
  name?: string;
  /** 图标 */
  icon?: string;
  /** 子路由 */
  routes?: IRouteConfig[];
  /** 重定向 */
  redirect?: string;
  /** 布局包装器 */
  wrappers?: string[];
  /** 是否隐藏子菜单 */
  hideChildrenInMenu?: boolean;
  /** 是否在菜单中隐藏 */
  hideInMenu?: boolean;
}

/**
 * 主题配置接口
 */
export interface IThemeConfig {
  /** 主题模式 */
  mode: 'light' | 'dark';
  /** 主色调 */
  primaryColor?: string;
  /** 字体家族 */
  fontFamily?: string;
}

/**
 * 布局配置接口
 */
export interface ILayoutConfig {
  /** 布局类型 */
  layout?: 'side' | 'top' | 'mix';
  /** 导航主题 */
  navTheme?: 'light' | 'dark';
  /** 固定头部 */
  fixedHeader?: boolean;
  /** 固定侧边栏 */
  fixSiderbar?: boolean;
}
