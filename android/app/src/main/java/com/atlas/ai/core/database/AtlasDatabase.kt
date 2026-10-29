package com.atlas.ai.core.database

import android.content.Context
import androidx.room.*
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.atlas.ai.data.local.*

@Database(entities = [Message::class, Memory::class, Conversation::class, ConversationSelection::class], version = 3, exportSchema = false)
abstract class AtlasDatabase : RoomDatabase() {
 abstract fun dao(): AtlasDao
 companion object {
  @Volatile private var instance: AtlasDatabase? = null
  fun getInstance(context: Context): AtlasDatabase = instance ?: synchronized(this) {
   instance ?: Room.databaseBuilder(context.applicationContext, AtlasDatabase::class.java, "atlas.db")
    .addMigrations(MIGRATION_1_2, MIGRATION_2_3).build().also { instance = it }
  }

  val MIGRATION_1_2 = object : Migration(1, 2) {
   override fun migrate(db: SupportSQLiteDatabase) {
    db.execSQL("ALTER TABLE messages ADD COLUMN delivery TEXT NOT NULL DEFAULT 'sent'")
    db.execSQL("ALTER TABLE messages ADD COLUMN requestId TEXT NOT NULL DEFAULT ''")
    db.execSQL("ALTER TABLE messages ADD COLUMN deliveryError TEXT DEFAULT NULL")
   }
  }
  val MIGRATION_2_3 = object : Migration(2, 3) {
   override fun migrate(db: SupportSQLiteDatabase) {
    db.execSQL("ALTER TABLE messages ADD COLUMN conversationId TEXT NOT NULL DEFAULT ''")
    db.execSQL("UPDATE messages SET conversationId=CASE WHEN scope='demo' THEN 'demo-main' ELSE 'android-' || scope END")
    db.execSQL("CREATE TABLE IF NOT EXISTS conversations (scope TEXT NOT NULL, id TEXT NOT NULL, title TEXT NOT NULL, createdAt INTEGER NOT NULL, updatedAt INTEGER NOT NULL, messageCount INTEGER NOT NULL, preview TEXT NOT NULL, serverAvailable INTEGER NOT NULL, beforeCursor INTEGER, hasMore INTEGER NOT NULL, PRIMARY KEY(scope,id))")
    db.execSQL("INSERT INTO conversations SELECT scope,conversationId,'Imported chat',MIN(createdAt),MAX(createdAt),COUNT(*),'',1,NULL,0 FROM messages GROUP BY scope,conversationId")
    db.execSQL("CREATE TABLE IF NOT EXISTS conversation_selection (scope TEXT NOT NULL PRIMARY KEY, id TEXT NOT NULL)")
    db.execSQL("INSERT INTO conversation_selection SELECT scope,id FROM conversations")
   }
  }

 }
}
