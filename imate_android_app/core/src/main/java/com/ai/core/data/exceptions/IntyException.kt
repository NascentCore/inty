package com.ai.core.data.exceptions

data class IntyException(
    val code: Int,
    val msg: String
): Exception()