/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import kotlinx.coroutines.delay

/**
 * 每日登录奖励庆祝横幅。
 *
 * 使用场景：用户满足 24 小时登录奖励条件并成功领取 Boost Points 时，
 * 在当前页面中心位置短暂显示。
 * 视觉效果：居中圆角卡片，左侧奖杯图标，右侧标题 + 积分副标题，
 * 伴随淡入缩放出现并自动消失。
 * 可配置项：积分 points、显示开关 isVisible、自动消失时长 autoDismissMillis、
 * 外部 modifier 与 dismiss 回调。
 */
@Composable
fun DailyLoginRewardBanner(
    points: Int,
    isVisible: Boolean,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    autoDismissMillis: Long = UiConfigs.DailyLoginRewardBanner.AutoDismissMillis,
) {
    val shouldShow = isVisible && points > 0
    val animationMillis = UiConfigs.DailyLoginRewardBanner.AnimationMillis

    AnimatedVisibility(
        visible = shouldShow,
        enter =
            fadeIn(tween(animationMillis)) +
                scaleIn(tween(animationMillis), initialScale = 0.92f),
        exit =
            fadeOut(tween(animationMillis)) +
                scaleOut(tween(animationMillis), targetScale = 0.92f),
        modifier = modifier,
    ) {
        Surface(
            shape = RoundedCornerShape(UiConfigs.DailyLoginRewardBanner.CornerRadius),
            tonalElevation = UiConfigs.DailyLoginRewardBanner.Elevation,
            shadowElevation = UiConfigs.DailyLoginRewardBanner.Elevation,
            color = MaterialTheme.colorScheme.surface,
            modifier = Modifier.widthIn(max = UiConfigs.DailyLoginRewardBanner.MaxWidth),
        ) {
            Row(
                modifier =
                    Modifier.padding(
                        horizontal = UiConfigs.DailyLoginRewardBanner.HorizontalPadding,
                        vertical = UiConfigs.DailyLoginRewardBanner.VerticalPadding,
                    ),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    imageVector = Icons.Rounded.EmojiEvents,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(UiConfigs.DailyLoginRewardBanner.IconSize),
                )
                Spacer(modifier = Modifier.width(UiConfigs.DailyLoginRewardBanner.IconTextSpacing))
                Column {
                    Text(
                        text = stringResource(R.string.boost_daily_login_reward_title),
                        color = MaterialTheme.colorScheme.onSurface,
                        style =
                            MaterialTheme.typography.titleMedium.copy(
                                fontWeight = FontWeight.Bold,
                            ),
                    )
                    Spacer(modifier = Modifier.height(UiConfigs.DailyLoginRewardBanner.TextSpacing))
                    Text(
                        text =
                            stringResource(
                                R.string.boost_daily_login_reward_subtitle,
                                points,
                            ),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }
    }

    LaunchedEffect(shouldShow, autoDismissMillis) {
        if (!shouldShow) return@LaunchedEffect
        delay(autoDismissMillis)
        onDismiss()
    }
}
