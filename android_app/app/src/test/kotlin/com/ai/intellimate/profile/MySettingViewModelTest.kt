package com.ai.intellimate.profile

import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.http.services.ImageService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.mockito.MockedStatic
import org.mockito.Mockito

/**
 * 极简单元测试：验证头像上传成功时，ViewModel 会用返回的 URL 更新 avatar 字段。
 */
class MySettingViewModelTest {

    private val testDispatcher = UnconfinedTestDispatcher()

    private lateinit var vm: MySettingViewModel

    private lateinit var imageServiceMock: MockedStatic<ImageService>

    @OptIn(ExperimentalCoroutinesApi::class)
    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        vm = MySettingViewModel()
        imageServiceMock = Mockito.mockStatic(ImageService::class.java)
    }

    @OptIn(ExperimentalCoroutinesApi::class)
    @After
    fun tearDown() {
        imageServiceMock.close()
        Dispatchers.resetMain()
    }

    @Test
    fun onSave_updatesAvatarOnUploadSuccess() = runTest(testDispatcher) {
        // 准备：初始资料，avatar 指向本地文件路径（仅用于触发逻辑）
        val localFileUri = "file:///tmp/avatar.jpg"
        vm.init(UserProfile(avatar = localFileUri))
        // 标记头像已变更
        val setAvatarMethod = MySettingViewModel::class.java.getDeclaredMethod("setAvatar", android.net.Uri::class.java)
        setAvatarMethod.isAccessible = true
        setAvatarMethod.invoke(vm, android.net.Uri.parse(localFileUri))

        // stub: ImageService 返回服务端 URL
        imageServiceMock.`when`<Any> {
            ImageService.uploadUserAvatar(Mockito.any())
        }.thenReturn("https://cdn.example.com/avatar-123.jpg")

        // 执行
        vm.onSave()

        // 断言：avatar 更新为服务端 URL
        val avatar = vm.userProfile.value.avatar
        assertEquals("https://cdn.example.com/avatar-123.jpg", avatar)
        // 额外 sanity check：非空
        assertTrue(avatar?.isNotBlank() == true)
    }
}
