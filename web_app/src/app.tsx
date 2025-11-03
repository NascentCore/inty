import '@ant-design/v5-patch-for-react-19';
import type { IInitialState } from '@/types';
import { hasToken, logger, getOrCreateDeviceId } from '@/utils';
import { guestLogin } from '@/services/auth';

/**
 * 获取应用初始状态
 * 在应用启动时执行
 * @see https://umijs.org/docs/api/runtime-config#getinitialstate
 */
export async function getInitialState(): Promise<IInitialState> {
  // 检查是否存在本地 token
  const tokenExists = await hasToken();
  
  if (!tokenExists) {
    logger.info('未找到本地 token，开始自动访客登录');
    
    try {
      // 获取或创建设备 ID
      const deviceId = await getOrCreateDeviceId();
      
      // 自动访客登录
      const result = await guestLogin({
        device_id: deviceId,
        system_language: navigator.language || 'en-US',
      });
      
      if (result.code === 200) {
        logger.info('访客登录成功', {
          guest_id: result.data.guest_id,
          is_new_guest: result.data.is_new_guest,
        });
      } else {
        logger.error('访客登录失败', result);
      }
    } catch (err) {
      logger.error('自动访客登录异常', err);
    }
  } else {
    logger.info('检测到本地 token，跳过访客登录');
  }

  return {
    name: 'IntelliMate',
  };
}
