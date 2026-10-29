package com.atlas.ai.core.database

import androidx.room.*
import kotlinx.coroutines.flow.Flow
import com.atlas.ai.data.local.*

@Dao interface AtlasDao {
 @Query("SELECT * FROM conversations WHERE scope = :scope ORDER BY updatedAt DESC, id") fun conversations(scope: String): Flow<List<Conversation>>
 @Query("SELECT * FROM conversations WHERE scope = :scope ORDER BY updatedAt DESC, id") suspend fun conversationList(scope: String): List<Conversation>
 @Query("SELECT * FROM conversations WHERE scope = :scope AND id = :id") suspend fun conversation(scope: String, id: String): Conversation?
 @Upsert suspend fun putConversation(conversation: Conversation)
 @Query("UPDATE conversations SET serverAvailable=0 WHERE scope=:scope") suspend fun markUnavailable(scope: String)
 @Query("DELETE FROM conversations WHERE scope=:scope AND id=:id") suspend fun removeConversation(scope: String, id: String)
 @Query("DELETE FROM messages WHERE scope=:scope AND conversationId=:id") suspend fun clearConversationMessages(scope: String, id: String)
 @Transaction suspend fun deleteConversationCache(scope: String, id: String) { clearConversationMessages(scope,id); removeConversation(scope,id) }
 @Upsert suspend fun selectConversation(selection: ConversationSelection)
 @Query("SELECT id FROM conversation_selection WHERE scope=:scope") suspend fun selectedConversation(scope: String): String?
 @Query("SELECT * FROM messages WHERE scope=:scope AND conversationId=:id ORDER BY createdAt,rowid") fun conversationMessages(scope: String, id: String): Flow<List<Message>>
 @Query("SELECT * FROM messages WHERE scope=:scope AND conversationId=:conversation AND role=:role AND (requestId=:requestId OR (requestId='' AND id=:requestId)) LIMIT 1") suspend fun messageForRequest(scope: String, conversation: String, requestId: String, role: String): Message?
 @Query("SELECT COUNT(*) FROM messages WHERE scope=:scope AND conversationId=:id AND delivery='sent'") suspend fun sentCount(scope: String,id: String): Int
 @Transaction suspend fun syncConversationList(scope: String, active: List<Conversation>, deleted: List<String>) {
  markUnavailable(scope)
  for(id in deleted) deleteConversationCache(scope,id)
  for(item in active) putConversation(item)
 }
 @Transaction suspend fun saveHistory(items: List<Message>, conversation: Conversation) {
  for(item in items) insert(item)
  putConversation(conversation)
 }
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
