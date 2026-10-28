package com.atlas.ai.core.database

import android.content.Context
import androidx.room.*
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.atlas.ai.data.local.*

@Database(entities = [Message::class, Memory::class], version = 2, exportSchema = false)
abstract class AtlasDatabase : RoomDatabase() {
 abstract fun dao(): AtlasDao
 companion object {
  @Volatile private var instance: AtlasDatabase? = null
  fun getInstance(context: Context): AtlasDatabase = instance ?: synchronized(this) {
   instance ?: Room.databaseBuilder(context.applicationContext, AtlasDatabase::class.java, "atlas.db")
    .addMigrations(MIGRATION_1_2).build().also { instance = it }
  }

  val MIGRATION_1_2 = object : Migration(1, 2) {
   override fun migrate(db: SupportSQLiteDatabase) {
    db.execSQL("ALTER TABLE messages ADD COLUMN delivery TEXT NOT NULL DEFAULT 'sent'")
    db.execSQL("ALTER TABLE messages ADD COLUMN requestId TEXT NOT NULL DEFAULT ''")
    db.execSQL("ALTER TABLE messages ADD COLUMN deliveryError TEXT DEFAULT NULL")
   }
  }
 }
}
