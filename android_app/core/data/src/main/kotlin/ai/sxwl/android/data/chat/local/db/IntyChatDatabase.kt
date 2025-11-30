package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

import ai.sxwl.android.utils.Utils
import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [ChatMessageEntity::class, ChatSyncStateEntity::class],
    version = 1,
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
                        ?: Room.databaseBuilder(context, IntyChatDatabase::class.java, DATABASE_NAME)
                            .fallbackToDestructiveMigration()
                            .build()
                            .also { instance = it }
                }
        }
    }
}
