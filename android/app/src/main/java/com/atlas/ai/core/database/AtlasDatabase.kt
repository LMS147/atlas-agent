package com.atlas.ai.core.database

import androidx.room.*
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.atlas.ai.data.local.*

@Database(entities = [Message::class, Memory::class], version = 2, exportSchema = false)
abstract class AtlasDatabase : RoomDatabase() {
 abstract fun dao(): AtlasDao
 companion object {
  val MIGRATION_1_2 = object : Migration(1, 2) {
   override fun migrate(db: SupportSQLiteDatabase) {
    db.execSQL("ALTER TABLE messages ADD COLUMN delivery TEXT NOT NULL DEFAULT 'sent'")
    db.execSQL("ALTER TABLE messages ADD COLUMN requestId TEXT NOT NULL DEFAULT ''")
    db.execSQL("ALTER TABLE messages ADD COLUMN deliveryError TEXT DEFAULT NULL")
   }
  }
 }
}
