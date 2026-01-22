package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.request.crossfade
import coil3.size.Size
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import com.inty.api.models.api.v1.ai.agents.Agent

/**
 * VIP 角色解锁对话框
 *
 * 用于显示 VIP 角色的解锁选项，包括：
 * - 角色背景图片
 * - 角色名称
 * - 使用积分解锁按钮
 * - 订阅解锁按钮
 *
 * 预期视觉效果：
 * - 对话框背景使用角色背景图片，带有渐变遮罩
 * - 角色名称居中显示在顶部区域
 * - 两个按钮垂直排列，使用项目主色调渐变
 * - 右上角有关闭按钮
 *
 * @param agent 角色信息，包含背景图片和名称
 * @param unlockByCredits 点击积分解锁按钮的回调
 * @param unlockBySub 点击订阅解锁按钮的回调
 * @param onDismissRequest 关闭对话框的回调
 * @param modifier 修饰符
 */
@Composable
fun VipAgentUnlockDialog(
    agent: AgentInfo,
    unlockByCredits: () -> Unit,
    unlockBySub: () -> Unit,
    onDismissRequest: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val configuration = LocalConfiguration.current

    Dialog(
        onDismissRequest = onDismissRequest,
        properties =
            DialogProperties(
                dismissOnBackPress = true,
                dismissOnClickOutside = true,
                usePlatformDefaultWidth = false,
            ),
    ) {
        Box(
            modifier =
                modifier
                    .fillMaxWidth()
                    .heightIn(min = UiConfigs.Size.ChatDialogMinHeight)
                    .padding(horizontal = UiConfigs.Padding.DialogEdge)
                    .clip(RoundedCornerShape(UiConfigs.Shape.VipDialog))
        ) {
            // 背景图片
            val backgroundUrl = agent.getLargeBackground() ?: agent.getLargeAvatar()
            if (backgroundUrl != null) {
                val containerWidthPx =
                    remember(configuration.screenWidthDp) {
                        with(density) { configuration.screenWidthDp.dp.toPx().toInt() }
                    }
                val containerHeightPx =
                    remember {
                        with(density) { UiConfigs.Size.ChatDialogMinHeight.toPx().toInt() }
                    }

                val imageRequest =
                    remember(backgroundUrl) {
                        ImageRequest.Builder(context)
                            .data(
                                getCdnImageUrl(
                                    backgroundUrl,
                                    width = UiConfigs.CharacterProfile.CDN_STATIC_BACKGROUND_WIDTH,
                                    quality = UiConfigs.CharacterProfile.CDN_IMAGE_QUALITY,
                                ) ?: backgroundUrl
                            )
                            .size(Size(containerWidthPx, containerHeightPx))
                            .crossfade(true)
                            .build()
                    }

                AsyncImage(
                    modifier = Modifier.matchParentSize(),
                    model = imageRequest,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                )
            }

            // 渐变遮罩
            Box(
                modifier =
                    Modifier.matchParentSize()
                        .background(
                            brush =
                                Brush.verticalGradient(
                                    colors =
                                        listOf(
                                            Color.Black.copy(alpha = 0.3f),
                                            Color.Black.copy(alpha = 0.7f),
                                        )
                                )
                        )
            )

            // 内容区域
            Column(
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(
                            horizontal = UiConfigs.Padding.DialogContentHorizontal,
                            vertical = UiConfigs.Padding.DialogContentVertical,
                        ),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.SpaceBetween,
            ) {
                // 顶部占位
                Spacer(Modifier.height(UiConfigs.Spacing.VipHeroPlaceholder))

                // 角色名称
                androidx.compose.material3.Text(
                    text = agent.name,
                    fontSize = UiConfigs.Typography.Title,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    textAlign = TextAlign.Center,
                )

                Spacer(Modifier.height(UiConfigs.Spacing.Medium))

                // 提示文字
                androidx.compose.material3.Text(
                    text = stringResource(R.string.vip_character_chat_locked_content),
                    fontSize = UiConfigs.Typography.Body,
                    fontWeight = FontWeight.Normal,
                    color = UiConfigs.Colors.VipSecondaryText,
                    textAlign = TextAlign.Center,
                    modifier =
                        Modifier.fillMaxWidth()
                            .padding(horizontal = UiConfigs.Padding.TextBlock),
                )

                Spacer(Modifier.height(UiConfigs.Spacing.XLarge))

                // 订阅按钮
                HeartPrimaryButton(
                    btnText = stringResource(R.string.vip_character_chat_locked_cta),
                    onClick = unlockBySub
                )

                Spacer(Modifier.height(UiConfigs.Spacing.Medium))

                // 积分解锁按钮
                HeartSecondaryButton(
                    btnText = stringResource(R.string.unlock_with_credits),
                    onClick = unlockByCredits
                )
            }

            // 关闭按钮
            IconButton(
                onClick = onDismissRequest,
                modifier = Modifier.align(Alignment.TopEnd)
            ) {
                Image(
                    painter = painterResource(R.drawable.close),
                    contentDescription = stringResource(R.string.close)
                )
            }
        }
    }
}

/**
 * 次要按钮（用于积分解锁）
 *
 * 预期视觉效果：
 * - 使用半透明背景，带有边框
 * - 文字颜色为白色
 * - 点击时有反馈效果
 */
@Composable
private fun HeartSecondaryButton(
    btnText: String,
    enable: Boolean = true,
    onClick: () -> Unit = {}
) {
    Box(
        modifier =
            Modifier.fillMaxWidth(UiConfigs.Fractions.PrimaryButtonWidth)
                .height(UiConfigs.Size.PrimaryButtonHeight)
                .clip(RoundedCornerShape(UiConfigs.Shape.PrimaryButton))
                .alpha(if (enable) 1f else UiConfigs.Alpha.DisabledButton)
                .background(
                    color = Color.White.copy(alpha = 0.2f),
                    shape = RoundedCornerShape(UiConfigs.Shape.PrimaryButton)
                )
                .clickable(enabled = enable, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        androidx.compose.material3.Text(
            text = btnText,
            fontSize = UiConfigs.Typography.Button,
            lineHeight = UiConfigs.LineHeight.Button,
            fontWeight = FontWeight.Normal,
            color = Color.White,
            textAlign = TextAlign.Center,
        )
    }
}

/**
 * 主要按钮（用于订阅解锁）
 *
 * 预期视觉效果：
 * - 使用项目主色调渐变背景
 * - 文字颜色为白色
 * - 点击时有反馈效果
 */
@Composable
private fun HeartPrimaryButton(
    btnText: String,
    enable: Boolean = true,
    onClick: () -> Unit = {}
) {
    Box(
        modifier =
            Modifier.fillMaxWidth(UiConfigs.Fractions.PrimaryButtonWidth)
                .height(UiConfigs.Size.PrimaryButtonHeight)
                .clip(RoundedCornerShape(UiConfigs.Shape.PrimaryButton))
                .alpha(if (enable) 1f else UiConfigs.Alpha.DisabledButton)
                .background(
                    brush = Brush.horizontalGradient(colors = UiConfigs.Colors.PrimaryGradient)
                )
                .clickable(enabled = enable, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        androidx.compose.material3.Text(
            text = btnText,
            fontSize = UiConfigs.Typography.Button,
            lineHeight = UiConfigs.LineHeight.Button,
            fontWeight = FontWeight.Normal,
            color = Color.White,
            textAlign = TextAlign.Center,
        )
    }
}

@Preview
@Composable
private fun PreviewVipAgentUnlockDialog() {
    val mockAgent =
        AgentInfo(
            id = "preview-agent",
            name = "VIP Character",
            background = "https://example.com/background.jpg",
            avatar = "https://example.com/avatar.jpg",
        )

    VipAgentUnlockDialog(
        agent = mockAgent,
        unlockByCredits = {},
        unlockBySub = {},
        onDismissRequest = {},
    )
}