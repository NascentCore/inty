package com.ai.intellimate.ui.components

import android.content.Context
import android.view.Gravity
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.VideoView
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.net.toUri
import androidx.lifecycle.compose.LifecycleResumeEffect

/** 自定义全屏视频播放器。继承VideoView并重写onMeasure方法保证全屏显示。 */
private class FullScreenVideoView(context: Context) : VideoView(context) {

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = getDefaultSize(0, widthMeasureSpec)
        val height = getDefaultSize(0, heightMeasureSpec)
        setMeasuredDimension(width, height)
    }
}

/** 使用背景视频播放器组件。AndroidView包装自定义VideoView，实现循环播放和性能优化。 */
@Composable
fun BackgroundVideoPlayer(modifier: Modifier = Modifier) {
    var videoView by remember { mutableStateOf<VideoView?>(null) }

    AndroidView(
        factory = { ctx ->
            FrameLayout(ctx).apply {
                removeAllViews()
                layoutParams =
                    ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT,
                    )

                videoView =
                    FullScreenVideoView(ctx).apply {
                        layoutParams =
                            FrameLayout.LayoutParams(
                                FrameLayout.LayoutParams.MATCH_PARENT,
                                FrameLayout.LayoutParams.MATCH_PARENT,
                                Gravity.CENTER,
                            )
// 设置视频路径
                        val videoPath = "android.resource://${ctx.packageName}/raw/subscribe_bg"
                        setVideoURI(videoPath.toUri())
//循环设置播放
                        setOnPreparedListener { mediaPlayer ->
                            mediaPlayer.isLooping = true
// 静音播放，避免干扰用户体验
                            mediaPlayer.setVolume(0f, 0f)
                        }
// 开始播放
                        start()
                    }

                addView(videoView)
            }
        },
        modifier = modifier.fillMaxSize(),
    )

    LifecycleResumeEffect(null) {
        videoView?.start()
        onPauseOrDispose { videoView?.stopPlayback() }
    }
}
