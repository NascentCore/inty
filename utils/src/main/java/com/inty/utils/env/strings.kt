package com.inty.utils.env

import com.inty.utils.AppEnv

fun getStringByResId(stringResId: Int) = AppEnv.context.getString(stringResId)