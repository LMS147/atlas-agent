package com.atlas.ai.core.database

import androidx.room.*
import kotlinx.coroutines.flow.Flow
import com.atlas.ai.data.local.*

@Dao interface AtlasDao {
 @Query("SELECT * FROM messages WHERE scope = :scope ORDER BY createdAt, rowid") fun messages(scope: String): Flow<List<Message>>
 @Upsert suspend fun insert(message: Message)
 @Query("SELECT * FROM messages WHERE scope = :scope AND id = :id LIMIT 1") suspend fun message(scope: String, id: String): Message?
 @Query("UPDATE messages SET delivery = 'retryable', deliveryError = 'The app closed before the reply was received. Check for the reply.' WHERE scope = :scope AND delivery = 'pending'") suspend fun recoverInterrupted(scope: String)
 @Transaction suspend fun complete(user: Message, assistant: Message) {
  insert(assistant)
  insert(user.copy(delivery = "sent", deliveryError = null))
 }
 @Query("SELECT * FROM memories WHERE scope = :scope ORDER BY section, id") fun memories(scope: String): Flow<List<Memory>>
 @Query("SELECT COUNT(*) FROM memories WHERE scope = :scope") suspend fun memoryCount(scope: String): Int
 @Query("DELETE FROM memories WHERE scope = :scope") suspend fun clearMemories(scope: String)
 @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun insertMemories(items: List<Memory>)
 @Transaction suspend fun replaceMemories(scope: String, items: List<Memory>) { clearMemories(scope); insertMemories(items) }
 @Query("DELETE FROM messages WHERE scope = :scope") suspend fun clearMessages(scope: String)
}
