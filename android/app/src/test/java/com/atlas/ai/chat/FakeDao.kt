package com.atlas.ai.chat

import com.atlas.ai.core.database.AtlasDao
import com.atlas.ai.data.local.*
import com.atlas.ai.domain.model.DeliveryStatus
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map

internal class FakeDao : AtlasDao {
 private val rows = linkedMapOf<String,Message>()
 private val updates = MutableStateFlow<List<Message>>(emptyList())
 private val memoryUpdates = MutableStateFlow<List<Memory>>(emptyList())
 private val chats = linkedMapOf<Pair<String,String>,Conversation>()
 private val chatUpdates = MutableStateFlow<List<Conversation>>(emptyList())
 private val selected = mutableMapOf<String,String>()
 override fun messages(scope:String):Flow<List<Message>> = updates.map { list -> list.filter { it.scope==scope }.sortedBy { it.createdAt } }
 override fun conversationMessages(scope:String,id:String):Flow<List<Message>> = updates.map { list -> list.filter { it.scope==scope && it.conversationId==id }.sortedBy { it.createdAt } }
 override suspend fun insert(message:Message) { rows[message.id]=message; updates.value=rows.values.toList() }
 override suspend fun message(scope:String,id:String)=rows[id]?.takeIf { it.scope==scope }
 override suspend fun messageForRequest(scope:String,conversation:String,requestId:String,role:String)=rows.values.firstOrNull { it.scope==scope && it.conversationId==conversation && it.role==role && (it.requestId==requestId || it.requestId.isEmpty() && it.id==requestId) }
 override suspend fun sentCount(scope:String,id:String)=rows.values.count { it.scope==scope && it.conversationId==id && it.delivery==DeliveryStatus.SENT }
 override suspend fun recoverInterrupted(scope:String) { rows.values.filter { it.scope==scope && it.delivery==DeliveryStatus.PENDING }.toList().forEach { insert(it.copy(delivery=DeliveryStatus.RETRYABLE,deliveryError="App interrupted")) } }
 override fun memories(scope:String):Flow<List<Memory>> = memoryUpdates.map { list -> list.filter { it.scope==scope } }
 override suspend fun memoryCount(scope:String)=memoryUpdates.value.count { it.scope==scope }
 override suspend fun clearMemories(scope:String) { memoryUpdates.value=memoryUpdates.value.filterNot { it.scope==scope } }
 override suspend fun insertMemories(items:List<Memory>) { memoryUpdates.value=memoryUpdates.value+items }
 override suspend fun clearMessages(scope:String) { rows.values.filter { it.scope==scope }.map { it.id }.forEach { rows.remove(it) }; updates.value=rows.values.toList() }
 override suspend fun clearConversationMessages(scope:String,id:String) { rows.values.filter { it.scope==scope && it.conversationId==id }.map { it.id }.forEach { rows.remove(it) }; updates.value=rows.values.toList() }
 override fun conversations(scope:String):Flow<List<Conversation>> = chatUpdates.map { list -> list.filter { it.scope==scope }.sortedByDescending { it.updatedAt } }
 override suspend fun conversationList(scope:String)=chats.values.filter { it.scope==scope }.sortedByDescending { it.updatedAt }
 override suspend fun conversation(scope:String,id:String)=chats[scope to id]
 override suspend fun putConversation(conversation:Conversation) { chats[conversation.scope to conversation.id]=conversation; chatUpdates.value=chats.values.toList() }
 override suspend fun markUnavailable(scope:String) { chats.values.filter { it.scope==scope }.toList().forEach { putConversation(it.copy(serverAvailable=false)) } }
 override suspend fun removeConversation(scope:String,id:String) { chats.remove(scope to id); chatUpdates.value=chats.values.toList() }
 override suspend fun selectConversation(selection:ConversationSelection) { selected[selection.scope]=selection.id }
 override suspend fun selectedConversation(scope:String)=selected[scope]
}
