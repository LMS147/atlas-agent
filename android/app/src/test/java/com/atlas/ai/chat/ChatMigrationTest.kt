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
  val db = Room.databaseBuilder(context, AtlasDatabase::class.java, name).addMigrations(AtlasDatabase.MIGRATION_1_2,AtlasDatabase.MIGRATION_2_3).allowMainThreadQueries().build()
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
   sql.query("SELECT conversationId FROM messages WHERE id='old-message'").use { cursor -> assertTrue(cursor.moveToFirst()); assertEquals("android-workspace",cursor.getString(0)) }
   sql.query("SELECT title FROM conversations WHERE scope='workspace' AND id='android-workspace'").use { cursor -> assertTrue(cursor.moveToFirst()); assertEquals("Imported chat",cursor.getString(0)) }
   assertEquals("android-workspace",db.dao().selectedConversation("workspace"))
   val user = Message("new-user", "workspace", "user", "Question", createdAt = 10)
   db.dao().insert(user)
   db.dao().complete(user, Message("new-user-reply", "workspace", "assistant", "Answer", createdAt = 10))
   sql.query("SELECT id FROM messages WHERE createdAt=10 ORDER BY createdAt,rowid").use { cursor ->
    assertTrue(cursor.moveToFirst()); assertEquals("new-user", cursor.getString(0))
    assertTrue(cursor.moveToNext()); assertEquals("new-user-reply", cursor.getString(0))
   }
  } finally { db.close(); context.deleteDatabase(name) }
 }
 @Test fun versionTwoUpgradePreservesPendingRequestAndWorkspaceSelection() = runBlocking {
  val context=ApplicationProvider.getApplicationContext<Context>()
  val name="v2-${UUID.randomUUID()}.db"
  val file=context.getDatabasePath(name)
  file.parentFile!!.mkdirs()
  SQLiteDatabase.openOrCreateDatabase(file,null).use { old ->
   old.execSQL("CREATE TABLE messages (id TEXT NOT NULL PRIMARY KEY,scope TEXT NOT NULL,role TEXT NOT NULL,text TEXT NOT NULL,createdAt INTEGER NOT NULL,delivery TEXT NOT NULL DEFAULT 'sent',requestId TEXT NOT NULL DEFAULT '',deliveryError TEXT DEFAULT NULL)")
   old.execSQL("CREATE TABLE memories (scope TEXT NOT NULL,id TEXT NOT NULL,section TEXT NOT NULL,fact TEXT NOT NULL,PRIMARY KEY(scope,id))")
   old.execSQL("INSERT INTO messages VALUES ('pending','workspace','user','Recover me',10,'pending','same-uuid',NULL)")
   old.execSQL("INSERT INTO messages VALUES ('demo-row','demo','user','Demo chat',20,'sent','demo-id',NULL)")
   old.version=2
  }
  val db=Room.databaseBuilder(context,AtlasDatabase::class.java,name).addMigrations(AtlasDatabase.MIGRATION_1_2,AtlasDatabase.MIGRATION_2_3).allowMainThreadQueries().build()
  try {
   val sql=db.openHelper.writableDatabase
   assertEquals("android-workspace",db.dao().selectedConversation("workspace"))
   assertEquals("demo-main",db.dao().selectedConversation("demo"))
   val pending=db.dao().message("workspace","pending")!!
   assertEquals("same-uuid",pending.requestId)
   assertEquals("pending",pending.delivery)
   assertEquals("android-workspace",pending.conversationId)
   db.dao().recoverInterrupted("workspace")
   assertEquals("retryable",db.dao().message("workspace","pending")!!.delivery)
   assertEquals(2,sql.query("SELECT COUNT(*) FROM conversations").use { it.moveToFirst(); it.getInt(0) })
  } finally { db.close(); context.deleteDatabase(name) }
 }

}
