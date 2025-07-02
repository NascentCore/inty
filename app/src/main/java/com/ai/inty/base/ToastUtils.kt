package com.ai.inty.base

import android.widget.Toast
import com.inty.utils.AppEnv
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object ToastUtils {

    suspend fun showToast(msg: String) = withContext(Dispatchers.Main) {
        val toast: Toast = Toast.makeText(AppEnv.context, msg, Toast.LENGTH_SHORT)
        toast.show()
    }

    suspend fun showToast(stringResId: Int) = withContext(Dispatchers.Main) {
        val toast: Toast = Toast.makeText(AppEnv.context, AppEnv.context.getString(stringResId), Toast.LENGTH_SHORT)
        toast.show()
    }

    suspend fun showToast(stringResId: Int, vararg formatArgs: Any) = withContext(Dispatchers.Main) {
        val message = AppEnv.context.getString(stringResId, *formatArgs)
        val toast: Toast = Toast.makeText(AppEnv.context, message, Toast.LENGTH_SHORT)
        toast.show()
    }

}