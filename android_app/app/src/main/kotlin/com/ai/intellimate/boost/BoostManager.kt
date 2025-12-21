/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.services.AgentService
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch

/** Boost 功能的统一入口，负责协调仓库与业务方。 */
object BoostManager {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val defaultState = MutableStateFlow(BoostState())
    private val defaultLeaderboard = MutableStateFlow<List<BoostLeaderboardEntry>>(emptyList())
    private val _events = MutableSharedFlow<BoostEvent>(extraBufferCapacity = 8)

    private var repository: BoostRepository? = null

    val boostState: StateFlow<BoostState>
        get() = repository?.stateFlow ?: defaultState

    val leaderboard: StateFlow<List<BoostLeaderboardEntry>>
        get() = repository?.leaderboardFlow ?: defaultLeaderboard

    val events: SharedFlow<BoostEvent> = _events.asSharedFlow()

    fun initialize(context: Context) {
        if (repository != null) return
        repository = BoostRepository(context.applicationContext)
    }

    fun recordChatTokens(agentInfo: AgentInfo?, message: String) {
        if (agentInfo == null || message.isBlank()) return
        val repo = repository ?: return
        val points =
            BoostCalculator.tokensToPoints(BoostCalculator.estimateTokensFromMessage(message))
        if (points <= 0) return
        scope.launch {
            repo.addPoints(points, PointSource.Chat(agentInfo.id))
            logPointsEvent(PointSource.Chat(agentInfo.id), points)
        }
    }

    fun recordAssistantMessage(agentInfo: AgentInfo?) {
        if (agentInfo == null) return
        val repo = repository ?: return
        scope.launch {
            repo.addPoints(BoostConfig.CHAT_MESSAGE_POINT_REWARD, PointSource.Chat(agentInfo.id))
            logPointsEvent(
                PointSource.Chat(agentInfo.id),
                BoostConfig.CHAT_MESSAGE_POINT_REWARD,
                agentInfo.name,
            )
        }
    }

    fun recordImageGeneration(agentInfo: AgentInfo?) {
        if (agentInfo == null) return
        val repo = repository ?: return
        val points = BoostCalculator.imageGenerationPoints()
        scope.launch {
            repo.addPoints(points, PointSource.Image(agentInfo.id))
            logPointsEvent(PointSource.Image(agentInfo.id), points)
        }
    }

    fun recordAudioPlayback(agentId: String, agentName: String?) {
        val repo = repository ?: return
        val points = BoostCalculator.audioPlaybackPoints()
        scope.launch {
            repo.addPoints(points, PointSource.Audio(agentId))
            logPointsEvent(PointSource.Audio(agentId), points, agentName)
        }
    }

    suspend fun claimDailyReward(): Int {
        val repo = repository ?: throw BoostException(BoostError.NotInitialized)
        val claimed = repo.claimDailyReward()
        _events.emit(BoostEvent.PointsEarned(PointSource.SignIn, claimed))
        logFirebaseEvent("boost_daily_reward_claimed", mapOf("points" to claimed))
        return claimed
    }

    suspend fun boostAgent(agentInfo: AgentInfo, requestedPoints: Int): BoostResult {
        val repo = repository ?: throw BoostException(BoostError.NotInitialized)
        val available = boostState.value.availablePoints
        val normalized = BoostCalculator.normalizeBoostAmount(requestedPoints, available)
        if (normalized <= 0) throw BoostException(BoostError.NotEnoughPoints)

        // 1. 本地 boost 操作
        val info = repo.boostAgent(agentInfo, normalized)
        val result = BoostResult(info, normalized)

        // 2. 同步到后端（异步，不阻塞）
        scope.launch {
            try {
                val updateResult =
                    AgentService.updateAgentEnergyPoints(
                        agentId = agentInfo.id,
                        energyPointsDelta = normalized,
                    )
                when (updateResult) {
                    is ApiResult.Success -> {
                        LogUtils.d(
                            "BoostManager",
                            "Successfully synced boost to backend: agentId=${agentInfo.id}, points=$normalized",
                        )
                        logFirebaseEvent(
                            "boost_synced_to_backend",
                            mapOf(
                                "agent_id" to agentInfo.id,
                                "agent_name" to agentInfo.name,
                                "points" to normalized,
                            ),
                        )
                    }
                    is ApiResult.Error -> {
                        LogUtils.w(
                            "BoostManager",
                            "Failed to sync boost to backend: agentId=${agentInfo.id}, error=${updateResult.message}",
                        )
                        logFirebaseEvent(
                            "boost_sync_failed",
                            mapOf(
                                "agent_id" to agentInfo.id,
                                "agent_name" to agentInfo.name,
                                "points" to normalized,
                                "error" to (updateResult.message ?: "unknown"),
                            ),
                        )
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("BoostManager", "Exception syncing boost to backend", e)
                logFirebaseEvent(
                    "boost_sync_exception",
                    mapOf(
                        "agent_id" to agentInfo.id,
                        "agent_name" to agentInfo.name,
                        "points" to normalized,
                        "exception" to e.javaClass.simpleName,
                    ),
                )
            }
        }

        // 3. 发送本地事件（立即返回）
        _events.emit(
            BoostEvent.BoostSuccess(
                agentId = agentInfo.id,
                agentName = agentInfo.name,
                pointsSpent = normalized,
                totalBoosts = info.boostCount,
            )
        )
        logFirebaseEvent(
            "boost_invested",
            mapOf(
                "agent_id" to agentInfo.id,
                "agent_name" to agentInfo.name,
                "points" to normalized,
                "total_boosts" to info.boostCount,
            ),
        )
        return result
    }

    fun requestManualPoints(points: Int) {
        val repo = repository
        if (repo == null) {
            LogUtils.e("BoostManager", "requestManualPoints: repository is null, BoostManager not initialized")
            return
        }
        if (points <= 0) {
            LogUtils.w("BoostManager", "requestManualPoints: invalid points value: $points")
            return
        }
        scope.launch {
            try {
                repo.addPoints(points, PointSource.Manual)
                logPointsEvent(PointSource.Manual, points)
                LogUtils.d("BoostManager", "requestManualPoints: successfully added $points points")
            } catch (e: Exception) {
                LogUtils.e("BoostManager", "requestManualPoints: failed to add points: ${e.message}", e)
            }
        }
    }

    private suspend fun logPointsEvent(
        source: PointSource,
        points: Int,
        agentName: String? = null,
    ) {
        _events.emit(BoostEvent.PointsEarned(source, points))
        val params =
            FirebaseManager.safeEventParams(
                "source" to source.analyticsName,
                "points" to points,
                "agent_name" to (agentName ?: ""),
            )
        FirebaseManager.logEvent("boost_token_earned", params)
    }

    private fun logFirebaseEvent(event: String, params: Map<String, Any?>) {
        val safeParams = params.map { it.key to (it.value ?: "") }.toTypedArray()
        FirebaseManager.logEvent(event, FirebaseManager.safeEventParams(*safeParams))
    }
}

sealed class BoostEvent {
    data class PointsEarned(val source: PointSource, val points: Int) : BoostEvent()

    data class BoostSuccess(
        val agentId: String,
        val agentName: String,
        val pointsSpent: Int,
        val totalBoosts: Int,
    ) : BoostEvent()

    data class Error(val error: BoostError) : BoostEvent()
}
