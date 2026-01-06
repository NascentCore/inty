package com.ai.intellimate.explore

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import com.ai.intellimate.R

/**
 * Explore 搜索浮层：点击顶部放大镜后出现的全屏搜索界面。
 * - 背景使用半透明深色蒙层，参考设计稿截图 2。
 * - 仅在键盘的 Search/放大镜动作触发后执行搜索，避免增量查询。
 * - 结果区使用 Explore 角色卡复用一致的卡片体验，点击角色后会沿用 Explorer 的跳转逻辑。
 *
 * @param innerPadding 传入 Explore 页面外部留白（底部导航高度）以确保安全区域。
 * @param searchResults 匹配到的角色列表。
 * @param isSearching 搜索请求是否执行中，用于显示 loading。
 * @param hasSearchExecuted 是否已经尝试过搜索，用于切换空状态/提示。
 * @param onDismiss 关闭浮层的回调，负责恢复 Explore 原页面。
 * @param onQuerySubmit 触发搜索的回调，由上层负责实际查询逻辑。
 * @param onClickAgent 点击角色卡片的回调（保持与 Explore 主视图一致）。
 */
@Composable
fun ExploreSearchOverlay(
    modifier: Modifier = Modifier,
    innerPadding: PaddingValues,
    searchResults: List<AgentInfo>,
    isSearching: Boolean,
    hasSearchExecuted: Boolean,
    onDismiss: () -> Unit,
    onQuerySubmit: (String) -> Unit,
    onClickAgent: (AgentInfo) -> Unit,
) {
    var searchText by rememberSaveable { mutableStateOf("") }
    val focusRequester = remember { FocusRequester() }
    val focusManager = LocalFocusManager.current
    val keyboardController = LocalSoftwareKeyboardController.current
    val bottomPadding = innerPadding.calculateBottomPadding()

    LaunchedEffect(Unit) { focusRequester.requestFocus() }

    BackHandler {
        focusManager.clearFocus(force = true)
        onDismiss()
    }

    Box(
        modifier =
            modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.98f))
                .windowInsetsPadding(WindowInsets.statusBars)
                .padding(bottom = bottomPadding)
                .navigationBarsPadding()
                .clickable {}
    ) {
        Column(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                TextField(
                    value = searchText,
                    onValueChange = { searchText = it },
                    modifier = Modifier.weight(1f).focusRequester(focusRequester),
                    placeholder = {
                        Text(text = stringResource(R.string.explore_search_placeholder))
                    },
                    singleLine = true,
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.Filled.Search,
                            contentDescription = null,
                            tint = Color.White.copy(alpha = 0.9f),
                        )
                    },
                    trailingIcon = {
                        if (searchText.isNotEmpty()) {
                            IconButton(onClick = { searchText = "" }) {
                                Icon(
                                    imageVector = Icons.Filled.Clear,
                                    contentDescription =
                                        stringResource(R.string.explore_search_clear_desc),
                                    tint = Color.White,
                                )
                            }
                        }
                    },
                    shape = RoundedCornerShape(32.dp),
                    colors =
                        TextFieldDefaults.colors(
                            focusedContainerColor = Color.White.copy(alpha = 0.12f),
                            unfocusedContainerColor = Color.White.copy(alpha = 0.08f),
                            disabledContainerColor = Color.White.copy(alpha = 0.08f),
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            cursorColor = Color.White,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent,
                        ),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions =
                        KeyboardActions(
                            onSearch = {
                                keyboardController?.hide()
                                focusManager.clearFocus(force = true)
                                onQuerySubmit(searchText)
                            }
                        ),
                )

                TextButton(
                    onClick = {
                        searchText = ""
                        focusManager.clearFocus(force = true)
                        onDismiss()
                    }
                ) {
                    Text(text = stringResource(R.string.explore_search_cancel), color = Color.White)
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            when {
                isSearching -> {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(color = Color.White)
                    }
                }

                searchResults.isNotEmpty() -> {
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(2),
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        contentPadding = PaddingValues(bottom = 32.dp),
                    ) {
                        items(searchResults, key = { it.id }) { agent ->
                            // 对创建于7天内的角色显示 "new" tag
                            ExploreCharacterCard(
                                modifier = Modifier,
                                agentInfo = agent,
                                onClick = {
                                    focusManager.clearFocus(force = true)
                                    onClickAgent(agent)
                                },
                                shouldPlayAnimated = false,
                                showNewTag = isCreatedWithin7Days(agent),
                            )
                        }
                    }
                }

                hasSearchExecuted -> {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(
                            text = stringResource(R.string.explore_search_empty),
                            color = Color.White.copy(alpha = 0.85f),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                }

                else -> {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(
                            text = stringResource(R.string.explore_search_hint_text),
                            color = Color.White.copy(alpha = 0.7f),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                }
            }
        }
    }
}
