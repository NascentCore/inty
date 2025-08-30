package com.ai.inty.base

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.view.View
import android.view.Window
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.window.DialogWindowProvider
import kotlin.math.roundToInt

@Composable
fun BottomSheetDialog(
    modifier: Modifier = Modifier,
    visible: Boolean,
    cancelable: Boolean = true,
    canceledOnTouchOutside: Boolean = true,
    onDismissRequest: () -> Unit,
    content: @Composable () -> Unit
) {
    BackHandler(enabled = visible, onBack = {
        if (cancelable) {
            onDismissRequest()
        }
    })
    Box(modifier = modifier) {
        AnimatedVisibility(
            visible = visible,
            enter = fadeIn(animationSpec = tween(durationMillis = 400, easing = LinearEasing)),
            exit = fadeOut(animationSpec = tween(durationMillis = 400, easing = LinearEasing))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(color = Color.Transparent)
                    .clickableNoRipple {
                        if (canceledOnTouchOutside) {
                            onDismissRequest()
                        }
                    }
            )
        }
        InnerDialog(
            visible = visible,
            content = content
        )
    }
}

@Composable
private fun BoxScope.InnerDialog(
    visible: Boolean,
    content: @Composable () -> Unit
) {
    var offsetY by remember {
        mutableFloatStateOf(value = 0f)
    }
    val offsetYAnimate by animateFloatAsState(targetValue = offsetY, label = "")
    AnimatedVisibility(
        modifier = Modifier
            .align(alignment = Alignment.BottomCenter)
            .offset(offset = {
                IntOffset(0, offsetYAnimate.roundToInt())
            }),
        visible = visible,
        enter = slideInVertically(
            animationSpec = tween(durationMillis = 400, easing = LinearOutSlowInEasing),
            initialOffsetY = {
                2 * it
            }
        ),
        exit = slideOutVertically(
            animationSpec = tween(durationMillis = 400, easing = LinearOutSlowInEasing),
            targetOffsetY = {
                it
            }
        )
    ) {
        DisposableEffect(key1 = null) {
            onDispose {
                offsetY = 0f
            }
        }
        Box {
            content()
        }
    }
}

private fun Modifier.clickableNoRipple(onClick: () -> Unit): Modifier =
    composed {
        clickable(
            onClick = onClick,
            indication = null,
            interactionSource = remember { MutableInteractionSource() }
        )
    }


//目前仅在chat page中使用
@Composable
fun DiaAmountLayout(
    content: @Composable DiaAmountWindowScope.() -> Unit
) {
    DiaAmountWindowScopeInstance.content()
}

interface DiaAmountWindowScope {
    @Composable
    fun SetDiaAmount(dimAmount: Float)
}

private object DiaAmountWindowScopeInstance : DiaAmountWindowScope {
    @Composable
    override fun SetDiaAmount(dimAmount: Float) {
        val curView = LocalView.current
        /* 更改dialog window的透明度 */
        LaunchedEffect(curView,dimAmount) {
            try {
                val window = curView.findWindow() ?: return@LaunchedEffect
                val lp = window.attributes
                lp.dimAmount = dimAmount
                window.attributes = lp
            } catch (e: Throwable) {
                e.printStackTrace()
            }
        }
    }

    private tailrec fun Context.findWindow(): Window? = when (this) {
        is Activity -> window
        is ContextWrapper -> baseContext.findWindow()
        else -> null
    }

    private fun View.findWindow(): Window? =
        (parent as? DialogWindowProvider)?.window ?: context.findWindow()

}
