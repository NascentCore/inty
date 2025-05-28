package com.inty.utils.log

import kotlinx.coroutines.asCoroutineDispatcher
import java.util.concurrent.Executors

val singleLogDispatcher = Executors.newFixedThreadPool(1).asCoroutineDispatcher()