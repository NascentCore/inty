import '@ant-design/v5-patch-for-react-19';
import type { IInitialState } from '@/types';
import { setDefaultTestToken } from '@/utils/token';

/**
 * 获取应用初始状态
 * 在应用启动时执行
 * @see https://umijs.org/docs/api/runtime-config#getinitialstate
 */
export async function getInitialState(): Promise<IInitialState> {
  // 【临时测试】设置默认 token（项目开发完成后需删除此调用）
  await setDefaultTestToken();

  return {
    name: 'IntelliMate',
  };
}
