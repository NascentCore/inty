package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

import ai.sxwl.android.utils.Utils
import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [ChatMessageEntity::class, ChatSyncStateEntity::class],
    version = 2,
    exportSchema = true,
)
abstract class IntyChatDatabase : RoomDatabase() {

    abstract fun chatMessageDao(): ChatMessageDao

    abstract fun chatSyncStateDao(): ChatSyncStateDao

    companion object {
        private const val DATABASE_NAME = "inty_chat.db"

        @Volatile private var instance: IntyChatDatabase? = null

        fun getInstance(context: Context = Utils.getApp()): IntyChatDatabase {
            return instance
                ?: synchronized(this) {
                    instance
                        ?: Room.databaseBuilder(
                                // 根据 Android 官方文档和 Room 最佳实践：
                                // 单例对象应使用 Application Context
                                // 数据库实例应使用 Application Context
                                // 避免持有短生命周期 Context 的引用
                                context.applicationContext,
                                IntyChatDatabase::class.java,
                                DATABASE_NAME,
                            )
                            .fallbackToDestructiveMigration()
                            .build()
                            .also { instance = it }
                }
        }
    }
}
