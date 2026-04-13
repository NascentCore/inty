package com.inty.imate.chat.local.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.ai.core.utils.Utils

@Database(entities = [MessageEntity::class], version = 1, exportSchema = false)
abstract class ImateChatDatabase : RoomDatabase() {

    abstract fun chatMessageDao(): ChatMessageDao

    companion object {
        private const val DATABASE_NAME = "imate_chat.db"

        @Volatile
        private var instance: ImateChatDatabase? = null

        fun getInstance(context: Context = Utils.getApp()): ImateChatDatabase {
            return instance
                ?: synchronized(this) {
                    instance
                        ?: Room.databaseBuilder(
                                context.applicationContext,
                                ImateChatDatabase::class.java,
                                DATABASE_NAME,
                            )
                            .fallbackToDestructiveMigration(true)
                            .build()
                            .also { instance = it }
                }
        }
    }
}
