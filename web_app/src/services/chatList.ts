/**
 * 聊天列表相关 API 服务
 * 使用 Inty SDK 实现
 */

import { createIntyClient, logger } from '@/utils';
import type { IApiResult, IChatListData, IChatListRequest, IChatItem } from '@/types';

/**
 * 获取聊天列表
 * 使用 Inty SDK 实现
 * @param params 请求参数
 * @returns 聊天列表
 */
export async function getChatList(
  params: IChatListRequest = {},
): Promise<IApiResult<IChatListData>> {
  try {
    // 获取已认证的客户端
    const client = await createIntyClient(true);
    
    // 将 page/page_size 转换为 skip/limit
    const page = params.page || 1;
    const pageSize = params.page_size || 20;
    const skip = (page - 1) * pageSize;
    const limit = pageSize;
    
    // 调用 SDK 的获取聊天列表接口
    // SDK 返回的是 Array<Chat>，不是包含 code/message/data 的对象
    const chatList = await client.api.v1.chats.list({
      skip,
      limit,
    });

    // 转换为项目的统一格式
    const result: IApiResult<IChatListData> = {
      code: 200,
      message: 'success',
      data: {
        data: (chatList || []) as IChatItem[],
        total: chatList?.length || 0,
        page: page,
        page_size: pageSize,
      },
    };

    return result;
  } catch (err: unknown) {
    logger.error('获取聊天列表失败', err);
    
    // 返回错误结果
    const error = err as { status?: number; message?: string };
    return {
      code: error.status || 500,
      message: error.message || '获取聊天列表失败',
      data: {
        data: [],
        total: 0,
        page: params.page || 1,
        page_size: params.page_size || 20,
      },
    };
  }
}

