package com.ai.imate.chat

import androidx.annotation.StringRes
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.core.data.exceptions.globalCatch
import com.ai.intellimate.R
import com.ai.imate.chat.data.InitChatOnboardingRepository
import com.ai.imate.chat.data.bean.AgentInfo
import com.ai.imate.chat.data.bean.CreateAgentRequest
import com.ai.imate.chat.data.bean.InitChatOnboardingGender
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class InitChatStep {
    Name,
    Gender,
    Appearance,
    Generating,
    Done,
}

sealed interface InitChatMessageText {
    data class Plain(val text: String) : InitChatMessageText
    data class Res(@StringRes val id: Int, val args: List<String> = emptyList()) : InitChatMessageText
    data class Parts(val parts: List<InitChatMessageText>) : InitChatMessageText
}

enum class InitChatRole { Agent, User }

data class InitChatMessage(
    val id: String,
    val role: InitChatRole,
    val text: InitChatMessageText,
)

enum class InitChatGender { Male, Female, NoPref }

data class InitChatUiState(
    val step: InitChatStep = InitChatStep.Name,
    val progress: Float = 0.08f,
    val headerTitle: InitChatMessageText = InitChatMessageText.Res(R.string.app_name),
    val headerSubtitle: InitChatMessageText =
        InitChatMessageText.Res(R.string.init_chat_header_subtitle_getting_to_know),
    val avatarUrl: String? = null,
    val messages: List<InitChatMessage> = emptyList(),
    val inputText: String = "",
    val nickname: String? = null,
    val gender: InitChatGender? = null,
    val appearance: String? = null,
    val doneEnabled: Boolean = false,
)

@HiltViewModel
class InitChatViewModel @Inject constructor(
    private val onboardingRepository: InitChatOnboardingRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(InitChatUiState())

    val uiState: StateFlow<InitChatUiState> = _uiState.asStateFlow()

    private var messageKeySeq = 0

    private var pendingCreatedAgent: AgentInfo? = null

    private fun nextMessageId(base: String): String = "${base}_${++messageKeySeq}"

    init {
        viewModelScope.launch {
            appendAgentLine(agentRes("hello", R.string.init_chat_msg_hello))
            delay(MESSAGE_STAGGER_MS)
            appendAgentLine(agentRes("learn", R.string.init_chat_msg_learn_about_you))
            delay(MESSAGE_STAGGER_MS)
            appendAgentLine(agentRes("ask_name", R.string.init_chat_msg_ask_name))
        }
    }

    fun onInputTextChanged(text: String) {
        _uiState.update { it.copy(inputText = text) }
    }

    fun submitName() {
        val name = _uiState.value.inputText.trim()
        if (name.isEmpty()) return

        _uiState.update {
            it.copy(
                nickname = name,
                inputText = "",
                step = InitChatStep.Gender,
                progress = 0.38f,
                headerTitle = InitChatMessageText.Plain(name),
                headerSubtitle = InitChatMessageText.Res(R.string.init_chat_header_subtitle_getting_to_know),
                messages = it.messages + userText(nextMessageId("user_name"), InitChatMessageText.Plain(name)),
            )
        }

        viewModelScope.launch {
            onboardingRepository.setNickname(name)
            delay(MESSAGE_STAGGER_MS)
            appendAgentLine(agentNameConfirm(name))
            delay(MESSAGE_STAGGER_MS)
            appendAgentLine(agentRes("ask_gender", R.string.init_chat_msg_ask_gender))
        }
    }

    fun selectGender(gender: InitChatGender) {
        val genderText =
            when (gender) {
                InitChatGender.Male ->
                    InitChatMessageText.Parts(
                        listOf(
                            InitChatMessageText.Res(R.string.init_chat_gender_male),
                            InitChatMessageText.Plain(" 💙"),
                        ),
                    )
                InitChatGender.Female ->
                    InitChatMessageText.Parts(
                        listOf(
                            InitChatMessageText.Res(R.string.init_chat_gender_female),
                            InitChatMessageText.Plain(" 💗"),
                        ),
                    )
                InitChatGender.NoPref -> InitChatMessageText.Res(R.string.init_chat_gender_no_pref)
            }

        _uiState.update { state ->
            val nickname = state.nickname.orEmpty()
            state.copy(
                gender = gender,
                step = InitChatStep.Appearance,
                progress = 0.66f,
                headerTitle = InitChatMessageText.Plain(nickname),
                messages = state.messages + userText(nextMessageId("user_gender"), genderText),
            )
        }

        viewModelScope.launch {
            onboardingRepository.setGender(gender.toOnboardingGender())
            delay(MESSAGE_STAGGER_MS)
            appendAgentLine(agentRes("gender_confirm", R.string.init_chat_msg_gender_confirm))
            delay(MESSAGE_STAGGER_MS)
            appendAgentLine(agentRes("ask_appearance", R.string.init_chat_msg_ask_appearance))
            delay(MESSAGE_STAGGER_MS)
            appendAgentLine(agentRes("appearance_examples", R.string.init_chat_msg_appearance_examples))
        }
    }

    fun submitAppearance() {
        val appearance = _uiState.value.inputText.trim()
        if (appearance.isEmpty()) return

        val nickname = _uiState.value.nickname.orEmpty()

        _uiState.update { state ->
            state.copy(
                appearance = appearance,
                inputText = "",
                step = InitChatStep.Generating,
                progress = 0.88f,
                headerTitle = InitChatMessageText.Plain(nickname),
                messages = state.messages + userText(nextMessageId("user_appearance"), InitChatMessageText.Plain(appearance)),
            )
        }

        viewModelScope.launch {
            delay(MESSAGE_STAGGER_MS)
            appendAgentLine(agentGeneratingVision(appearance))

            val prompt = buildAvatarPrompt(nickname = nickname, appearance = appearance, gender = _uiState.value.gender)
            var avatarUrl: String? = null
            var avatarOk = false
            globalCatch {
                val resp = onboardingRepository.generateAvatar(prompt)
                val extracted =
                    resp.urls.firstOrNull()?.takeIf { it.isNotBlank() }
                        ?: resp.url.takeIf { it.isNotBlank() }
                avatarUrl = extracted
                avatarOk = !extracted.isNullOrBlank()
            }
            if (!avatarOk) {
                _uiState.update { state ->
                    state.copy(
                        step = InitChatStep.Appearance,
                        progress = 0.66f,
                        inputText = "",
                    )
                }
                appendAgentLine(
                    InitChatMessage(
                        id = nextMessageId("agent_avatar_failed_retry"),
                        role = InitChatRole.Agent,
                        text = InitChatMessageText.Plain("Something went wrong. Please describe my appearance again."),
                    ),
                )
                return@launch
            }

            if (!avatarUrl.isNullOrBlank()) {
                onboardingRepository.setAvatarUrl(avatarUrl)
            }

            val genderApi = _uiState.value.gender.toApiGender()
            val createRequest =
                CreateAgentRequest(
                    name = nickname,
                    gender = genderApi,
                    background = avatarUrl,
                    intro = appearance,
                    opening = "",
                    visibility = "PRIVATE",
                )
            var createdId: String? = null
            var createdAgent: AgentInfo? = null
            globalCatch {
                val agent = onboardingRepository.createAgent(createRequest)
                if (!agent.id.isBlank()) {
                    createdAgent = agent
                    createdId = agent.id
                }
            }
            if (createdId.isNullOrBlank()) {
                _uiState.update { state ->
                    state.copy(
                        step = InitChatStep.Appearance,
                        progress = 0.66f,
                        inputText = "",
                    )
                }
                appendAgentLine(
                    InitChatMessage(
                        id = nextMessageId("agent_create_failed_retry"),
                        role = InitChatRole.Agent,
                        text =
                            InitChatMessageText.Plain(
                                "Something went wrong creating your companion. Please describe my appearance again.",
                            ),
                    ),
                )
                return@launch
            }

            pendingCreatedAgent = createdAgent

            delay(GENERATING_HOLD_MS)
            _uiState.update { state ->
                state.copy(
                    step = InitChatStep.Done,
                    progress = 1f,
                    headerSubtitle = InitChatMessageText.Res(R.string.init_chat_header_subtitle_ready),
                    avatarUrl = avatarUrl,
                    doneEnabled = true,
                    messages = state.messages + agentDoneIntro(nickname),
                )
            }
            delay(MESSAGE_STAGGER_MS)
            appendAgentLine(agentRes("done_ready", R.string.init_chat_msg_done_ready))
        }
    }

    fun confirmEnterChat() {
        val agent = pendingCreatedAgent ?: return
        pendingCreatedAgent = null
        _uiState.update { it.copy(doneEnabled = false) }
        viewModelScope.launch { onboardingRepository.setCreatedAgent(agent) }
    }

    private fun appendAgentLine(message: InitChatMessage) {
        _uiState.update { it.copy(messages = it.messages + message) }
    }

    private fun agentNameConfirm(name: String) =
        InitChatMessage(
            id = nextMessageId("agent_name_confirm"),
            role = InitChatRole.Agent,
            text =
                InitChatMessageText.Parts(
                    listOf(
                        InitChatMessageText.Res(R.string.init_chat_msg_love_name_prefix),
                        InitChatMessageText.Plain(name),
                        InitChatMessageText.Res(R.string.init_chat_msg_love_name_suffix),
                    ),
                ),
        )

    private fun agentGeneratingVision(appearance: String) =
        InitChatMessage(
            id = nextMessageId("agent_generating_vision"),
            role = InitChatRole.Agent,
            text =
                InitChatMessageText.Parts(
                    listOf(
                        InitChatMessageText.Res(R.string.init_chat_msg_generating_vision_prefix),
                        InitChatMessageText.Plain(appearance),
                        InitChatMessageText.Res(R.string.init_chat_msg_generating_vision_suffix),
                    ),
                ),
        )

    private fun agentDoneIntro(name: String) =
        InitChatMessage(
            id = nextMessageId("agent_done_intro"),
            role = InitChatRole.Agent,
            text =
                InitChatMessageText.Parts(
                    listOf(
                        InitChatMessageText.Res(R.string.init_chat_msg_done_intro),
                        InitChatMessageText.Plain(name),
                        InitChatMessageText.Res(R.string.init_chat_msg_done_intro_suffix),
                    ),
                ),
        )

    private fun agentRes(id: String, @StringRes textId: Int) =
        InitChatMessage(
            id = nextMessageId("agent_$id"),
            role = InitChatRole.Agent,
            text = InitChatMessageText.Res(textId),
        )

    private fun userText(id: String, text: InitChatMessageText) =
        InitChatMessage(
            id = id,
            role = InitChatRole.User,
            text = text,
        )

    private fun buildAvatarPrompt(
        nickname: String,
        appearance: String,
        gender: InitChatGender?,
    ): String {
        val genderHint =
            when (gender) {
                InitChatGender.Male -> "male"
                InitChatGender.Female -> "female"
                InitChatGender.NoPref, null -> ""
            }
        return listOfNotNull(
            nickname.takeIf { it.isNotBlank() }?.let { "portrait of $it" },
            genderHint.takeIf { it.isNotBlank() },
            appearance.takeIf { it.isNotBlank() },
            "single, adult, high detail, focus on expression, soft lighting",
        ).joinToString(", ")
    }

    private companion object {
        const val MESSAGE_STAGGER_MS = 380L
        const val GENERATING_HOLD_MS = 1300L
    }
}

private fun InitChatGender.toOnboardingGender(): InitChatOnboardingGender =
    when (this) {
        InitChatGender.Male -> InitChatOnboardingGender.Male
        InitChatGender.Female -> InitChatOnboardingGender.Female
        InitChatGender.NoPref -> InitChatOnboardingGender.NoPref
    }

private fun InitChatGender?.toApiGender(): String =
    when (this) {
        InitChatGender.Male -> "MALE"
        InitChatGender.Female -> "FEMALE"
        InitChatGender.NoPref, null -> "OTHER"
    }

