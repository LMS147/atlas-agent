package com.atlas.ai.chat

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.atlas.ai.core.database.AtlasDatabase
import com.atlas.ai.data.local.Message
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.util.UUID

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class ChatMigrationTest {
 @Test fun upgradePreservesHistoryMemoryAndStableMessageOrder() = runBlocking {
  val context = ApplicationProvider.getApplicationContext<Context>()
  val name = "migration-${UUID.randomUUID()}.db"
  val file = context.getDatabasePath(name)
  file.parentFile!!.mkdirs()
  SQLiteDatabase.openOrCreateDatabase(file, null).use { old ->
   old.execSQL("CREATE TABLE messages (id TEXT NOT NULL PRIMARY KEY, scope TEXT NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL, createdAt INTEGER NOT NULL)")
   old.execSQL("CREATE TABLE memories (scope TEXT NOT NULL, id TEXT NOT NULL, section TEXT NOT NULL, fact TEXT NOT NULL, PRIMARY KEY(scope,id))")
   old.execSQL("INSERT INTO messages VALUES ('old-message','workspace','user','Keep my chat',1)")
   old.execSQL("INSERT INTO memories VALUES ('workspace','old-memory','Projects','Keep my memory')")
   old.version = 1
  }
  val db = Room.databaseBuilder(context, AtlasDatabase::class.java, name).addMigrations(AtlasDatabase.MIGRATION_1_2).allowMainThreadQueries().build()
  try {
   val sql = db.openHelper.writableDatabase
   sql.query("SELECT text, delivery, requestId, deliveryError FROM messages WHERE id='old-message'").use { cursor ->
    assertTrue(cursor.moveToFirst())
    assertEquals("Keep my chat", cursor.getString(0))
    assertEquals("sent", cursor.getString(1))
    assertEquals("", cursor.getString(2))
    assertTrue(cursor.isNull(3))
   }
   sql.query("SELECT fact FROM memories").use { cursor -> assertTrue(cursor.moveToFirst()); assertEquals("Keep my memory", cursor.getString(0)) }
   val user = Message("new-user", "workspace", "user", "Question", createdAt = 10)
   db.dao().insert(user)
   db.dao().complete(user, Message("new-user-reply", "workspace", "assistant", "Answer", createdAt = 10))
   sql.query("SELECT id FROM messages WHERE createdAt=10 ORDER BY createdAt,rowid").use { cursor ->
    assertTrue(cursor.moveToFirst()); assertEquals("new-user", cursor.getString(0))
    assertTrue(cursor.moveToNext()); assertEquals("new-user-reply", cursor.getString(0))
   }
  } finally { db.close(); context.deleteDatabase(name) }
 }
}
