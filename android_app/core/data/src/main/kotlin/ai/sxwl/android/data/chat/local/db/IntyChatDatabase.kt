package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

import ai.sxwl.android.utils.Utils
import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(entities = [MessageEntity::class], version = 11, exportSchema = true)
abstract class IntyChatDatabase : RoomDatabase() {

    abstract fun chatMessageDao(): ChatMessageDao

    companion object {
        private const val DATABASE_NAME = "inty_chat.db"

        /** 10→11: 新增 message.model（MetaData.model），用于 debug 显示所用模型。 */
        private val MIGRATION_10_11 = object : Migration(10, 11) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE message ADD COLUMN model TEXT")
            }
        }

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
                            .addMigrations(MIGRATION_10_11)
                            .build()
                            .also { instance = it }
                }
        }
    }
}
