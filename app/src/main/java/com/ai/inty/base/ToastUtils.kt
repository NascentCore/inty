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


}