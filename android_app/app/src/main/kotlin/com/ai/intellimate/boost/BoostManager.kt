/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.firebase.FirebaseManager
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
        val points = BoostCalculator.tokensToPoints(BoostCalculator.estimateTokensFromMessage(message))
        if (points <= 0) return
        scope.launch {
            repo.addPoints(points, PointSource.Chat(agentInfo.id))
            logPointsEvent(PointSource.Chat(agentInfo.id), points)
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
        val info = repo.boostAgent(agentInfo, normalized)
        val result = BoostResult(info, normalized)
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
            )
        )
        return result
    }

    fun requestManualPoints(points: Int) {
        val repo = repository ?: return
        if (points <= 0) return
        scope.launch {
            repo.addPoints(points, PointSource.Manual)
            logPointsEvent(PointSource.Manual, points)
        }
    }

    private suspend fun logPointsEvent(source: PointSource, points: Int, agentName: String? = null) {
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
