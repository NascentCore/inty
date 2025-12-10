/*
 * CREATED_BY_AGENT
 */
package ai.sxwl.android.data.character.local.db

import ai.sxwl.android.utils.Utils
import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(entities = [CharacterEntity::class], version = 1, exportSchema = true)
abstract class CharacterDatabase : RoomDatabase() {

    abstract fun characterDao(): CharacterDao

    companion object {
        private const val DATABASE_NAME = "character.db"

        @Volatile private var instance: CharacterDatabase? = null

        fun getInstance(context: Context = Utils.getApp()): CharacterDatabase {
            return instance
                ?: synchronized(this) {
                    instance
                        ?: Room.databaseBuilder(
                                context.applicationContext,
                                CharacterDatabase::class.java,
                                DATABASE_NAME,
                            )
                            .fallbackToDestructiveMigration()
                            .build()
                            .also { instance = it }
                }
        }
    }
}
