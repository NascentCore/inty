package com.ai.inty.base

import android.view.Gravity
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.core.graphics.toColorInt
import com.inty.utils.AppEnv
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object ToastUtils {

    private var toast: Toast? = null


    suspend fun showToast(msg: String) = withContext(Dispatchers.Main) {
        if (toast == null) {
            toast = Toast(AppEnv.context)
        }
        toast?.setText(msg)
        toast?.show()
    }

    suspend fun showToast(stringResId: Int) = withContext(Dispatchers.Main) {
        if (toast == null) {
            toast = Toast(AppEnv.context)
        }
        toast?.setText(stringResId)
        toast?.show()
    }

    suspend fun showToast(stringResId: Int, vararg formatArgs: Any) =
        withContext(Dispatchers.Main) {
            val message = AppEnv.context.getString(stringResId, *formatArgs)
            if (toast == null) {
                toast = Toast(AppEnv.context)
            }
            toast?.setText(message)
            toast?.show()
        }

    /**
     * 显示长文本 Toast，自动处理换行和样式
     */
    suspend fun showLongTextToast(message: String, duration: Int = Toast.LENGTH_LONG) =
        withContext(Dispatchers.Main) {
            val context = AppEnv.context
            val toast = Toast(context)

            // 创建自定义布局
            val layout = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 16, 32, 16)
                setBackgroundColor("#CC333333".toColorInt())
            }

            // 创建文本视图
            val textView = TextView(context).apply {
                text = message
                setTextColor(android.graphics.Color.WHITE)
                textSize = 14f
                setLineSpacing(0f, 1.2f) // 设置行间距
                maxLines = 10 // 限制最大行数
                setPadding(0, 8, 0, 8)
            }

            layout.addView(textView)
            toast.view = layout
            toast.duration = duration
            toast.setGravity(Gravity.CENTER, 0, 0)
            toast.show()
        }
}
