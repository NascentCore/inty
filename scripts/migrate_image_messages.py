"""
数据迁移脚本：将独立的图片消息迁移到对应AI消息的meta_data
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from app.services.chat_history_service import get_chat_history_connection


def migrate_image_messages_to_metadata():
    """将独立的 image 消息迁移到对应 AI 消息的 meta_data"""

    logger.info("开始迁移图片消息到 meta_data")

    conn = get_chat_history_connection()

    try:
        # 1. 查找所有图片消息
        query = """
            SELECT id, session_id, message, meta_data 
            FROM chat_history 
            WHERE message->>'type' = 'image'
        """

        with conn.cursor() as cur:
            cur.execute(query)
            image_messages = cur.fetchall()

        logger.info(f"找到 {len(image_messages)} 条图片消息")

        migrated_count = 0
        skipped_count = 0
        error_count = 0

        for img_msg in image_messages:
            img_id, session_id, message_raw, meta_data_raw = img_msg

            logger.debug(f"处理图片消息 {img_id}, session_id={session_id}")

            try:
                # 解析消息数据
                if isinstance(message_raw, str):
                    message_data = json.loads(message_raw)
                elif isinstance(message_raw, dict):
                    message_data = message_raw
                else:
                    message_data = json.loads(str(message_raw))

                logger.debug(f"消息数据类型: {message_data.get('type')}")

                # 解析 meta_data
                if isinstance(meta_data_raw, str):
                    meta_data = json.loads(meta_data_raw)
                elif isinstance(meta_data_raw, dict):
                    meta_data = meta_data_raw
                else:
                    meta_data = {}

                # 2. 获取 source_message_id
                source_id = meta_data.get("source_message_id")
                if not source_id:
                    logger.warning(
                        f"图片消息 {img_id} 没有 source_message_id，直接删除。meta_data keys: {list(meta_data.keys())}"
                    )
                    # 直接删除无法关联的图片消息
                    with conn.cursor() as cur:
                        delete_query = "DELETE FROM chat_history WHERE id = %s"
                        cur.execute(delete_query, (img_id,))
                    logger.info(f"✅ 已删除无关联图片消息 {img_id}")
                    skipped_count += 1
                    continue

                logger.debug(f"source_message_id: {source_id}")

                # 3. 提取图片信息
                image_data = message_data.get("data", {})
                if not image_data.get("image_url"):
                    logger.warning(f"图片消息 {img_id} 没有 image_url，跳过")
                    skipped_count += 1
                    continue

                image_info = {
                    "generated_image": {
                        "image_url": image_data.get("image_url"),
                        "width": image_data.get("width"),
                        "height": image_data.get("height"),
                        "format": image_data.get("format", "jpeg"),
                        "prompt": image_data.get("prompt"),
                    }
                }

                logger.debug(f"图片信息: {image_info['generated_image']['image_url']}")

                # 为每个图片消息创建新的游标
                with conn.cursor() as cur:
                    # 4. 查询源消息的现有 meta_data
                    select_query = """
                        SELECT meta_data 
                        FROM chat_history 
                        WHERE session_id = %s AND id = %s
                    """
                    cur.execute(select_query, (session_id, source_id))
                    source_row = cur.fetchone()

                    if not source_row:
                        logger.warning(
                            f"源消息不存在: session_id={session_id}, id={source_id}"
                        )
                        skipped_count += 1
                        continue

                    logger.debug(f"找到源消息 {source_id}")

                    # 合并 meta_data
                    existing_meta = source_row[0] if source_row[0] else {}
                    if isinstance(existing_meta, str):
                        existing_meta = json.loads(existing_meta)

                    merged_meta = {**existing_meta, **image_info}

                    logger.debug(f"合并后的 meta_data keys: {list(merged_meta.keys())}")

                    # 5. 更新源消息的 meta_data
                    update_query = """
                        UPDATE chat_history 
                        SET meta_data = %s::jsonb
                        WHERE session_id = %s AND id = %s
                    """
                    cur.execute(
                        update_query, (json.dumps(merged_meta), session_id, source_id)
                    )

                    logger.debug(f"更新了源消息 {source_id} 的 meta_data")

                    # 6. 删除独立的图片消息
                    delete_query = "DELETE FROM chat_history WHERE id = %s"
                    cur.execute(delete_query, (img_id,))

                    logger.debug(f"删除了图片消息 {img_id}")

                migrated_count += 1
                logger.info(f"✅ 成功迁移图片消息 {img_id} -> 消息 {source_id}")

            except Exception as e:
                logger.error(f"❌ 迁移图片消息 {img_id} 失败: {str(e)}")
                import traceback

                logger.error(traceback.format_exc())
                error_count += 1
                continue

        # 提交事务
        conn.commit()

        logger.info(
            f"迁移完成！成功: {migrated_count}, 跳过: {skipped_count}, 失败: {error_count}"
        )

    except Exception as e:
        logger.error(f"迁移过程出错: {str(e)}")
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("图片消息迁移脚本")
    logger.info("=" * 60)

    try:
        migrate_image_messages_to_metadata()
        logger.success("✅ 迁移成功完成")
    except Exception as e:
        logger.error(f"❌ 迁移失败: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
