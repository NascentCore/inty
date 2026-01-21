/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

/** Boost 体系的基础常量配置，集中存放以避免魔法数字。 */
object BoostConfig {
    /** 每次 Boost 消耗的最小积分，所有投入都以该步长为单位。 */
    const val BOOST_STEP_POINTS = 100

    /** 每日签到基础奖励。 */
    const val DAILY_SIGN_IN_REWARD = 200

    /** 每日登录奖励（免费用户）。 */
    const val DAILY_LOGIN_REWARD_FREE = 10

    /** 每日登录奖励（订阅用户）。 */
    const val DAILY_LOGIN_REWARD_VIP = 20

    /** 订阅会员每月奖励。 */
    const val MONTHLY_VIP_REWARD = 500

    /** 文本 → token 的平均估算比例（字符数 / AVG_CHARS_PER_TOKEN）。 */
    const val AVG_CHARS_PER_TOKEN = 4.0

    /** token → point 的折算比例。 */
    const val TOKEN_TO_POINT_RATIO = 1.0

    /** 单条 AI 回复的基础能量奖励。 */
    const val CHAT_MESSAGE_POINT_REWARD = 1

    /** 单次图片生成折算的 token 量。 */
    const val IMAGE_TOKEN_COST = 600

    /** 单次语音播放折算的 token 量。 */
    const val AUDIO_TOKEN_COST = 120

    /** 每日通过行为可累积的最大积分，避免意外刷分。 */
    const val MAX_POINTS_PER_DAY = 10_000

    /** 排行榜展示数量上限。 */
    const val LEADERBOARD_LIMIT = 100

    /** MMKV 存储键名（已废弃，保留用于兼容性）。 */
    @Deprecated("使用 BoostStorage 内部常量", ReplaceWith("")) const val STORAGE_FILE_NAME = "boost_state"
}

/** 排行榜趋势展示类型。 */
enum class BoostTrend {
    UP,
    DOWN,
    FLAT,
}
