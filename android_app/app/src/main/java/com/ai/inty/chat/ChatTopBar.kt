package com.ai.inty.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter


private const val CHAT_TOP_BAR_AVATAR_SIZE = 30
private const val CHAT_TOP_BAR_AVATAR_PADDING = 3
private const val CHAT_TOP_BAR_CORNER_RADIUS = 20
private val CHAT_TOP_BAR_BACKGROUND_COLOR = Color(33, 0, 0, 77)
private const val CHAT_TOP_BAR_FOLLOW_BUTTON_SIZE = 20

private const val BACK_BUTTON_SIZE = 24
private const val MORE_BUTTON_SIZE = 20


/**
 * 聊天页面顶部栏组件
 */
@Composable
fun ChatTopBar(
    modifier: Modifier,
    agentInfo: AgentInfo,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
    onClickMore: () -> Unit,
    onFollowAgent: ((String) -> Unit)? = null,
) {
    val context = LocalContext.current

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // 返回按钮
        if (showBackButton) {
            IntyImage(
                modifier = Modifier
                    .size(BACK_BUTTON_SIZE.dp)
                    .noRippleClickable {
                        onBack?.invoke()
                    },
                model = R.drawable.back
            )
            Spacer(modifier = Modifier.width(8.dp))
        }

        Row(
            modifier = Modifier
                .background(
                    color = CHAT_TOP_BAR_BACKGROUND_COLOR,
                    shape = RoundedCornerShape(CHAT_TOP_BAR_CORNER_RADIUS.dp)
                )
                .noRippleClickable {
                    TheRouter.build(Constant.ROUTE_AGENT_INFO)
                        .withObject("agent", agentInfo)
                        .navigation(context)
                },
            verticalAlignment = Alignment.CenterVertically
        ) {
            IntyCircleImage(
                modifier = Modifier
                    .padding(CHAT_TOP_BAR_AVATAR_PADDING.dp)
                    .size(CHAT_TOP_BAR_AVATAR_SIZE.dp),
                url = agentInfo.avatar,
                placeholderResID = R.drawable.app_icon
            )

            Spacer(modifier = Modifier.width(6.dp))

            Text(
                text = agentInfo.name,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = Color.White
            )

            Spacer(modifier = Modifier.width(6.dp))

            if (!agentInfo.isFollowed) {
                IntyImage(
                    modifier = Modifier
                        .size(CHAT_TOP_BAR_FOLLOW_BUTTON_SIZE.dp)
                        .noRippleClickable { onFollowAgent?.invoke(agentInfo.id) },
                    model = R.drawable.btn_add
                )
            }

            Spacer(modifier = Modifier.width(8.dp))
        }

        Spacer(modifier = Modifier.weight(1f))

        IntyImage(
            modifier = Modifier
                .size(MORE_BUTTON_SIZE.dp)
                .noRippleClickable {
                    onClickMore()
                },
            model = R.drawable.icon_more
        )
    }
} 
