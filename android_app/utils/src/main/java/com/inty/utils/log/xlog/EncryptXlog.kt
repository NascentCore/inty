package com.inty.utils.log.xlog

import com.inty.utils.AppEnv
import com.tencent.mars.xlog.Xlog
import com.tencent.mars.xlog.Xlog.XLogConfig

// private key: 253c3cbb71500abaed306992867f3b54a83214fbfb86d26b372d8924194e52c0

object EncryptXlog {


    const val LEVEL_ALL = 0
    const val LEVEL_VERBOSE = 0
    const val LEVEL_DEBUG = 1
    const val LEVEL_INFO = 2
    const val LEVEL_WARNING = 3
    const val LEVEL_ERROR = 4
    const val LEVEL_FATAL = 5
    const val LEVEL_NONE = 6

    private var logInstancePtr: Long = 0

    private val logPath by lazy { AppEnv.dirs.logDir }
    private val cachePath by lazy { AppEnv.dirs.logDir }

    private const val PUB_KEY = "fb4c67bd462a8ac81c04e45a3c2edd9b58740d908019fae136f75dc77ef6e364bdf5e3dc072f97fbae6dcb42abb2d581cb59c2493a4b6545931a3359b8580832"

    private val xlog: Xlog

    init {
        val logConfig = XLogConfig()
        logConfig.level = Xlog.LEVEL_ALL
        logConfig.mode = Xlog.AppednerModeAsync
        logConfig.logdir = logPath
        logConfig.nameprefix = AppEnv.processName.lowercase().replace(":", "_")
        logConfig.compressmode = Xlog.ZLIB_MODE
        logConfig.compresslevel = Xlog.COMPRESS_LEVEL6
        logConfig.pubkey = PUB_KEY
        logConfig.cachedir = cachePath
        logConfig.cachedays = 0

        xlog = Xlog()
        logInstancePtr = xlog.newXlogInstance(logConfig)

        xlog.setMaxAliveTime(logInstancePtr, 60 * 60 * 24 * 30)

    }

    fun log(priority: Int, tag: String, message: String) {
        Xlog.logWrite2(logInstancePtr, priority, tag, "", "", 0, 0, 0, 0, message)
    }

    fun flush() {
        xlog.appenderFlush(logInstancePtr, false)
    }
}
