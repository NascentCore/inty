/**
 * 聊天列表相关 API 服务
 * 使用 Inty SDK 实现
 */

import { createIntyClient, logger } from '@/utils';
import type { IChatListRequest, IChatItem } from '@/types';

/**
 * 获取聊天列表
 * 使用 Inty SDK 实现
 * @param params 请求参数
 * @returns 聊天列表数组，失败时返回空数组
 */
export async function getChatList(
  params: IChatListRequest = {},
): Promise<IChatItem[]> {
  try {
    // 获取已认证的客户端
    const client = await createIntyClient(true);
    
    // 将 page/page_size 转换为 skip/limit
    const page = params.page || 1;
    const pageSize = params.page_size || 20;
    const skip = (page - 1) * pageSize;
    const limit = pageSize;
    
    // 调用 SDK 的获取聊天列表接口
    const chatList = await client.api.v1.chats.list({
      skip,
      limit,
    });
    logger.info('获取聊天列表响应', chatList);

    // 直接返回聊天列表数组
    return (chatList || []) as IChatItem[];
  } catch (err: unknown) {
    logger.error('获取聊天列表失败', err);
    
    // 返回空数组
    return [];
  }
}

