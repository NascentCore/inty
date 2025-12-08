package com.architecture.httplib.utils

import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.lang.reflect.Type

/**  */
object MoshiUtils {
    val moshiBuild: Moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()

    inline fun <reified T> fromJson(json: String): T? {
        val adapter = moshiBuild.adapter(T::class.java)
        return adapter.fromJson(json)
    }

    inline fun <reified T> toJson(t: T) = moshiBuild.adapter(T::class.java).toJson(t) ?: ""
}
