package com.ai.intellimate.ui.components

import android.content.Context
import android.view.Gravity
import android.view.View
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

/** 自定义视频播放器。 使用 crop 模式填充容器，超出部分裁剪。 */
private class AspectRatioVideoView(context: Context) : VideoView(context) {
    private var videoAspectRatio: Float? = null

    fun setVideoAspectRatio(width: Int, height: Int) {
        if (width > 0 && height > 0) {
            videoAspectRatio = width.toFloat() / height.toFloat()
            requestLayout()
        }
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val containerWidth = View.MeasureSpec.getSize(widthMeasureSpec)
        val containerHeight = View.MeasureSpec.getSize(heightMeasureSpec)

        // Crop 模式：填充整个容器，保持视频宽高比，超出部分裁剪
        var finalWidth: Int
        var finalHeight: Int

        videoAspectRatio?.let { aspectRatio ->
            val containerAspectRatio = containerWidth.toFloat() / containerHeight.toFloat()

            if (aspectRatio > containerAspectRatio) {
                // 视频更宽，以高度为准，宽度会超出
                finalHeight = containerHeight
                finalWidth = (containerHeight * aspectRatio).toInt()
            } else {
                // 视频更高，以宽度为准，高度会超出
                finalWidth = containerWidth
                finalHeight = (containerWidth / aspectRatio).toInt()
            }
        }
            ?: run {
                // 如果没有视频宽高比，填充整个容器
                finalWidth = containerWidth
                finalHeight = containerHeight
            }

        setMeasuredDimension(finalWidth, finalHeight)
    }
}

/** 背景视频播放器组件。 使用AndroidView包装自定义VideoView，实现循环播放和性能优化。 */
@Composable
fun BackgroundVideoPlayer(modifier: Modifier = Modifier) {
    var videoView by remember { mutableStateOf<AspectRatioVideoView?>(null) }

    AndroidView(
        factory = { ctx ->
            FrameLayout(ctx).apply {
                removeAllViews()
                layoutParams =
                    ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT,
                    )
                // 启用裁剪，超出容器的部分会被裁剪
                clipChildren = true
                clipToPadding = true

                videoView =
                    AspectRatioVideoView(ctx).apply {
                        layoutParams =
                            FrameLayout.LayoutParams(
                                FrameLayout.LayoutParams.MATCH_PARENT,
                                FrameLayout.LayoutParams.MATCH_PARENT,
                                Gravity.CENTER,
                            )

                        // 设置视频路径
                        val videoPath = "android.resource://${ctx.packageName}/raw/subscribe_bg"
                        setVideoURI(videoPath.toUri())

                        // 设置循环播放和宽高比
                        setOnPreparedListener { mediaPlayer ->
                            mediaPlayer.isLooping = true
                            // 静音播放，避免干扰用户体验
                            mediaPlayer.setVolume(0f, 0f)
                            // 获取视频宽高比并设置
                            val videoWidth = mediaPlayer.videoWidth
                            val videoHeight = mediaPlayer.videoHeight
                            if (videoWidth > 0 && videoHeight > 0) {
                                setVideoAspectRatio(videoWidth, videoHeight)
                            }
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
