package com.ai.intellimate.chat.ui

// CREATED_BY_AGENT: chat page back-to-top button

import ai.sxwl.android.design.noRippleClickable
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.vectorResource
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

@Composable
fun BackToTop(
    modifier: Modifier = Modifier,
    visible: Boolean,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    val config = UiConfigs.ChatPage.ScrollToBottomButton

    AnimatedVisibility(visible = visible, enter = fadeIn(), exit = fadeOut(), modifier = modifier) {
        Box(
            modifier =
                Modifier.size(config.ButtonSize)
                    .clip(CircleShape)
                    .border(
                        config.BorderWidth,
                        brush =
                            Brush.horizontalGradient(
                                colors =
                                    listOf(
                                        Color.White.copy(
                                            if (enabled) {
                                                config.BorderGradientStartAlpha
                                            } else {
                                                config.BorderGradientStartAlphaDisabled
                                            }
                                        ),
                                        Color.White.copy(config.BorderGradientEndAlpha),
                                    )
                            ),
                        shape = CircleShape,
                    )
                    .background(Color.Black.copy(alpha = config.BackgroundAlpha), CircleShape)
                    .alpha(if (enabled) 1f else config.DisabledAlpha)
                    .then(
                        if (enabled) {
                            Modifier.noRippleClickable(onClick = onClick)
                        } else {
                            Modifier
                        }
                    )
                    .padding(config.InnerPadding),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = ImageVector.vectorResource(R.drawable.keyboard_double_arrow_up_24px),
                contentDescription = "Back to top",
                modifier = Modifier.size(config.IconSize),
                tint = if (enabled) Color.White else Color.LightGray,
            )
        }
    }
}

