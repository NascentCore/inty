package com.ai.intellimate.agent.heartbeat

import ai.sxwl.android.data.character.local.db.FestivalMemory
import ai.sxwl.android.common.utils.HeartAppUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R

/** Debug 用节日记忆元数据块：背景透明度。 */
private const val DEBUG_METADATA_BACKGROUND_ALPHA = 0.08f

/** Debug 用节日记忆元数据块：文字颜色（青蓝）。 */
private val DEBUG_METADATA_TEXT_COLOR = Color(0xFF8DF0FF)

/** Debug 用节日记忆元数据块：字体大小与行高（与 AGENTS.md 约定一致，数值集中于此）。 */
private val DEBUG_METADATA_FONT_SIZE = 10.sp
private val DEBUG_METADATA_LINE_HEIGHT = 12.sp

/**
 * Debug 构建下展示单条节日记忆的全部元数据（id、agentId、festivalDate、festivalName、memory、title）。
 * 用于 Love Journal 卡片底部与聊天页节日记忆通知条，非 debug 不渲染。
 *
 * @param memory 节日记忆实体
 * @param modifier 可选布局修饰
 */
@Composable
fun FestivalMemoryDebugMetadata(
    memory: FestivalMemory,
    modifier: Modifier = Modifier,
) {
    if (!HeartAppUtils.isAppDebugMode()) return

    val lines =
        listOf(
            "id=${memory.id}",
            "agentId=${memory.agentId}",
            "festivalDate=${memory.festivalDate}",
            "festivalName=${memory.festivalName ?: "null"}",
            "memory=${memory.memory}",
            "title=${memory.title}",
        )

    Box(
        modifier =
            modifier
                .fillMaxWidth()
                .background(
                    Color.White.copy(alpha = DEBUG_METADATA_BACKGROUND_ALPHA),
                    RoundedCornerShape(dimensionResource(R.dimen.heartbeat_card_inner_spacing)),
                )
                .padding(
                    horizontal = dimensionResource(R.dimen.padding_small),
                    vertical = dimensionResource(R.dimen.padding_extra_small),
                )
    ) {
        Text(
            text = lines.joinToString(separator = "\n"),
            fontSize = DEBUG_METADATA_FONT_SIZE,
            lineHeight = DEBUG_METADATA_LINE_HEIGHT,
            color = DEBUG_METADATA_TEXT_COLOR,
        )
    }
}
