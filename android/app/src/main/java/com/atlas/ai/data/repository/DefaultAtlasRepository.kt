package com.atlas.ai.data.repository

import com.atlas.ai.core.database.AtlasDao
import com.atlas.ai.core.network.*
import com.atlas.ai.domain.model.DeliveryStatus
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import retrofit2.HttpException
import com.atlas.ai.data.local.*
import com.atlas.ai.data.model.*
import com.atlas.ai.data.remote.AtlasApi
import com.atlas.ai.domain.repository.AtlasRepository

import java.util.UUID
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.MediaType.Companion.toMediaType
import kotlinx.coroutines.flow.first
import java.io.IOException

class DefaultAtlasRepository(
 private val dao: AtlasDao,
 private val apiFactory: (String, String) -> AtlasApi = { url, token -> ApiFactory.create(url, token) }
) : AtlasRepository {
 private val chatMutex = Mutex()
 override var scope: String = "demo"; private set
 private var api: AtlasApi? = null
 override val demo get() = api == null
 override var offline: Boolean = false; private set
 override var conversationId: String = "demo-main"; private set
 override fun conversations() = dao.conversations(scope)
 override fun messages() = dao.conversationMessages(scope, conversationId)
 override fun memories() = dao.memories(scope)
 override fun useDemo() { api = null; scope = "demo"; conversationId = "demo-main"; offline = false }
 suspend override fun connect(url: String, token: String) {
  val normalized = ApiFactory.normalize(url)
  val candidate = apiFactory(normalized, token)
  val hash = java.security.MessageDigest.getInstance("SHA-256").digest((normalized + "\n" + token).toByteArray())
  val target = hash.joinToString("") { "%02x".format(it) }
  val local = dao.conversationList(target)
  var serverList: List<ConversationDto>? = null
  var cachedOnly = false
  try {
   require(candidate.health().status == "ok") { "Server is not ready" }
   serverList = candidate.conversations()
   if (serverList.none { !it.deleted } && local.isEmpty()) serverList = serverList + candidate.createConversation(ConversationName())
  } catch (error: IOException) {
   if (local.isEmpty()) throw error
   cachedOnly = true
  }
  if (serverList != null) syncList(target, serverList)
  dao.recoverInterrupted(target)
  scope = target
  api = candidate
  offline = cachedOnly
  chooseSelected()
 }
 private fun ConversationDto.cached(target: String, previous: Conversation? = null) = Conversation(
  target, id, title, created_at, updated_at, message_count, preview,
  serverAvailable = true, beforeCursor = previous?.beforeCursor, hasMore = previous?.hasMore ?: false
 )
 private suspend fun syncList(target: String, items: List<ConversationDto>) {
  val active = items.filterNot { it.deleted }.map { it.cached(target,dao.conversation(target,it.id)) }
  dao.syncConversationList(target,active,items.filter { it.deleted }.map { it.id })
 }
 private suspend fun chooseSelected() {
  val items = dao.conversationList(scope)
  val saved = dao.selectedConversation(scope)
  conversationId = items.firstOrNull { it.id == saved }?.id ?: items.firstOrNull()?.id.orEmpty()
  dao.selectConversation(ConversationSelection(scope,conversationId))
 }
 override suspend fun refreshConversations() {
  val remote = api ?: return
  syncList(scope,remote.conversations())
  offline = false
  chooseSelected()
 }
 override suspend fun newConversation(title: String) {
  val clean = title.trim()
  require(clean.isNotBlank() && clean.length <= 80) { "Titles must contain 1–80 characters." }
  val remote = api
  val item = if(remote != null) remote.createConversation(ConversationName(clean)).cached(scope)
   else Conversation(scope,"demo-${UUID.randomUUID()}",clean,System.currentTimeMillis(),System.currentTimeMillis())
  dao.putConversation(item)
  selectConversation(item.id)
 }
 override suspend fun selectConversation(id: String) {
  requireNotNull(dao.conversation(scope,id)) { "Conversation not found in this workspace." }
  conversationId = id
  dao.selectConversation(ConversationSelection(scope,id))
 }
 override suspend fun renameConversation(id: String, title: String) {
  val clean = title.trim()
  require(clean.isNotBlank() && clean.length <= 80) { "Titles must contain 1–80 characters." }
  val previous = requireNotNull(dao.conversation(scope,id))
  require(demo || previous.serverAvailable) { "This cached chat is unavailable on the server." }
  val updated = api?.renameConversation(id,ConversationName(clean))?.cached(scope,previous)
   ?: previous.copy(title=clean,updatedAt=System.currentTimeMillis())
  dao.putConversation(updated)
 }
 override suspend fun deleteConversation(id: String) {
  val item = requireNotNull(dao.conversation(scope,id))
  if(item.serverAvailable) api?.deleteConversation(id)
  dao.deleteConversationCache(scope,id)
  chooseSelected()
 }
 override suspend fun refreshHistory(earlier: Boolean) {
  val remote = api ?: return
  val current = dao.conversation(scope,conversationId) ?: return
  if(!current.serverAvailable) return
  if(earlier && !current.hasMore) return
  val page = remote.history(current.id,if(earlier) current.beforeCursor else null)
  val cachedMessages = mutableListOf<Message>()
  for(item in page.items) {
   val user = dao.messageForRequest(scope,current.id,item.request_id,"user")
   val baseId = user?.id ?: "$scope:${current.id}:${item.request_id}"
   val existing = dao.messageForRequest(scope,current.id,item.request_id,item.role)
   val id = existing?.id ?: if(item.role == "user") baseId else "$baseId-reply"
   cachedMessages.add(Message(id,scope,item.role,item.text,item.created_at,DeliveryStatus.SENT,item.request_id,null,current.id))
  }
  dao.saveHistory(cachedMessages,current.copy(beforeCursor=page.next_before,hasMore=page.has_more))
  offline = false
 }
 private suspend fun updateSummary(id: String) {
  val previous = dao.conversation(scope,id) ?: return
  val remote = api
  if(remote != null) {
   try { dao.putConversation(remote.conversation(id).cached(scope,previous)) }
   catch(e: CancellationException) { throw e }
   catch(_: Exception) { /* A cached reply remains successful even if a metadata refresh fails. */ }
  } else {
   val rows = dao.conversationMessages(scope,id).first()
   dao.putConversation(previous.copy(updatedAt=System.currentTimeMillis(),messageCount=rows.count { it.delivery==DeliveryStatus.SENT },preview=rows.lastOrNull()?.text.orEmpty().take(160)))
  }
 }
 suspend override fun seed() {
  dao.recoverInterrupted(scope)
  if (demo && dao.conversationList(scope).isEmpty()) {
   dao.putConversation(Conversation(scope,"demo-main","Demo chat",System.currentTimeMillis(),System.currentTimeMillis()))
  }
  chooseSelected()
  if (demo && dao.memoryCount(scope) == 0) dao.replaceMemories(scope, listOf(
   Memory(scope, "1", "Projects", "Build the Atlas Android companion with Kotlin and Jetpack Compose."),
   Memory(scope, "2", "User Preferences", "Keep replies helpful, honest, concise, and practical."),
   Memory(scope, "3", "Decisions", "The Groq API key stays on the Python server.")
  ))
 }
 suspend override fun refreshMemory() { api?.let { remote -> dao.replaceMemories(scope, remote.memories().map { Memory(scope, it.id, it.section, it.fact) }) } }
 suspend override fun send(text: String) = chatMutex.withLock {
  val content = text.trim()
  require(content.isNotEmpty() && content.length <= 8000) { "Messages must contain 1–8,000 characters." }
  if (demo && dao.conversation(scope,conversationId) == null) seed()
  val conversation = requireNotNull(dao.conversation(scope,conversationId)) { "Create or choose a conversation first." }
  require(demo || conversation.serverAvailable) { "This chat is only cached locally. Start a new conversation." }
  val id = UUID.randomUUID().toString()
  val message = Message(id, scope, "user", content, delivery = DeliveryStatus.PENDING, requestId = id, conversationId = conversationId)
  try { dao.insert(message) } catch (e: Exception) {
   if (e is CancellationException) throw e
   throw MessageNotSavedException(e)
  }
  deliver(message)
 }
 suspend override fun retry(id: String, newRequest: Boolean) = chatMutex.withLock {
  val message = requireNotNull(dao.message(scope, id)) { "This message is no longer in the current workspace." }
  require(message.role == "user" && message.conversationId == conversationId) { "Open this message’s conversation before retrying." }
  if (message.delivery == DeliveryStatus.SENT) return@withLock
  if (newRequest) require(message.delivery == DeliveryStatus.FAILED) { "Check for the existing reply first." }
  else require(message.delivery in setOf(DeliveryStatus.RETRYABLE,DeliveryStatus.UNCONFIRMED)) { "This request requires confirmation before sending again." }
  val pending = message.copy(
   delivery = DeliveryStatus.PENDING, deliveryError = null,
   requestId = if (newRequest) UUID.randomUUID().toString() else message.requestId.ifBlank { message.id }
  )
  dao.insert(pending)
  deliver(pending)
 }
 override suspend fun recover(id: String) = chatMutex.withLock {
  val message = requireNotNull(dao.message(scope,id)) { "Message not found in this workspace." }
  require(message.role == "user" && message.conversationId == conversationId)
  if(message.delivery == DeliveryStatus.SENT) return@withLock
  require(message.delivery in setOf(DeliveryStatus.RETRYABLE,DeliveryStatus.UNCONFIRMED))
  val pending = message.copy(delivery=DeliveryStatus.PENDING,deliveryError=null)
  dao.insert(pending)
  val remote = api
  if(remote == null && demo) { deliver(pending); return@withLock }
  try {
   val status = checkNotNull(remote).requestStatus(message.conversationId,message.requestId.ifBlank { message.id })
   if(status.request_id != message.requestId.ifBlank { message.id }) throw InvalidReplyException()
   when(status.status) {
    "done" -> {
     val reply = status.reply
     if(reply.isNullOrBlank()) throw InvalidReplyException()
     cacheReply(pending,reply)
     offline=false
     updateSummary(message.conversationId)
    }
    "pending" -> dao.insert(message.copy(delivery=DeliveryStatus.RETRYABLE,deliveryError="Atlas is still processing this request. Check again later."))
    "not_found" -> dao.insert(message.copy(delivery=DeliveryStatus.UNCONFIRMED,deliveryError="No request record yet. Retry delivery with the same request ID."))
    "failed", "interrupted" -> dao.insert(message.copy(delivery=DeliveryStatus.FAILED,deliveryError="The earlier request did not finish. Check memory before confirming a new request."))
    else -> throw InvalidReplyException()
   }
  } catch(e:Exception) {
   val delivery = if(e is HttpException && e.code() in setOf(401,403,404,410)) DeliveryStatus.FAILED else DeliveryStatus.RETRYABLE
   withContext(NonCancellable) { dao.insert(message.copy(delivery=delivery,deliveryError=ChatErrors.message(e))) }
   throw e
  }
 }
 private suspend fun cacheReply(message: Message, reply: String) {
  dao.complete(message, Message("${message.id}-reply", message.scope, "assistant", reply,
   createdAt=maxOf(System.currentTimeMillis(),message.createdAt+1),requestId=message.requestId,conversationId=message.conversationId))
 }
 private suspend fun deliver(message: Message) {
  val remote = api
  try {
   // Only explicit demo mode generates a local reply. Network failures never fall back to demo.
   val reply = if (message.scope == "demo" && remote == null) {
    "This is a demo conversation. Connect your Atlas server to receive real AI replies."
   } else {
    checkNotNull(remote) { "Connect to your Atlas server first." }
    remote.chat(ChatRequest(message.text, message.conversationId, message.requestId.ifBlank { message.id })).reply
   }
   if (reply.isNullOrBlank()) throw InvalidReplyException()
   cacheReply(message,reply)
  } catch (e: Exception) {
   val state = if (e is HttpException && e.code() in setOf(401, 403, 404, 409, 410, 422, 429, 502, 504)) DeliveryStatus.FAILED else DeliveryStatus.RETRYABLE
   withContext(NonCancellable) {
    dao.insert(message.copy(delivery = state, deliveryError = if(e is CancellationException) "Reply interrupted. Check for the reply." else ChatErrors.message(e)))
   }
   throw e
  }
  offline = false
  updateSummary(message.conversationId)
 }
 suspend override fun remember(section: String, fact: String) {
  val remote = api
  if (remote == null) dao.insertMemories(listOf(Memory(scope, UUID.randomUUID().toString(), section, fact)))
  else { remote.remember(MemoryRequest(section, fact)); refreshMemory() }
 }
 suspend override fun profile() = api?.agent() ?: AgentProfile(content = "I’m Atlas, your personal AI companion. I help with projects, learning, and automation.\n\nPersonality\nHelpful, honest, concise, and practical.\n\nDemo profile — the live identity will come from agent.md.")
 suspend override fun files(directory: String) = api?.files(directory) ?: listOf(FileItem("agent.md", "agent.md", false, 1254), FileItem("memory.md", "memory.md", false, 68), FileItem("backups", "backups", true))
 suspend override fun health() = api?.health() ?: Health("demo", "Preview data", 0)
 suspend override fun clearChat() = dao.clearConversationMessages(scope,conversationId)

 private fun live(): AtlasApi = requireNotNull(api) { "Connect your Atlas server to manage files, memory and metrics." }
 override suspend fun document(path: String) = live().document(path)
 override suspend fun download(path: String): ByteArray = live().download(path).use { body ->
  val bytes = com.atlas.ai.core.network.BoundedFiles.read(body.byteStream(),5 * 1024 * 1024)
  require(bytes.size <= 5 * 1024 * 1024) { "Download exceeds 5 MiB." }
  bytes
 }
 override suspend fun upload(name: String, bytes: ByteArray) {
  require(bytes.size <= 5 * 1024 * 1024) { "Uploads are limited to 5 MiB." }
  live().upload(name,bytes.toRequestBody("application/octet-stream".toMediaType()))
 }
 override suspend fun editFile(path: String, content: String, revision: String) { live().editFile(path,FileEdit(content,revision)) }
 override suspend fun editMemory(id: String, section: String, fact: String) { live().editMemory(id,MemoryRequest(section,fact)); refreshMemory() }
 override suspend fun deleteMemory(id: String) { live().deleteMemory(id); refreshMemory() }
 override suspend fun compactPlan() = live().compactPlan()
 override suspend fun compact(revision: String) { live().compact(CompactRequest(revision)); refreshMemory() }
 override suspend fun monitoring() = live().monitoring()
}
