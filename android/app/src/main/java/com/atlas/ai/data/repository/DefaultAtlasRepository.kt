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

class DefaultAtlasRepository(
 private val dao: AtlasDao,
 private val apiFactory: (String, String) -> AtlasApi = { url, token -> ApiFactory.create(url, token) }
) : AtlasRepository {
 private val chatMutex = Mutex()
 override var scope: String = "demo"; private set
 private var api: AtlasApi? = null
 override val demo get() = api == null
 override fun messages() = dao.messages(scope)
 override fun memories() = dao.memories(scope)
 override fun useDemo() { api = null; scope = "demo" }
 suspend override fun connect(url: String, token: String) {
  val normalized = ApiFactory.normalize(url)
  val candidate = apiFactory(normalized, token)
  require(candidate.health().status == "ok") { "Server is not ready" }
  // Separate server and credential identities to prevent account cache crossover.
  val hash = java.security.MessageDigest.getInstance("SHA-256").digest((normalized + "\n" + token).toByteArray())
  val targetScope = hash.joinToString("") { "%02x".format(it) }
  dao.recoverInterrupted(targetScope)
  scope = targetScope
  api = candidate
 }
 suspend override fun seed() {
  dao.recoverInterrupted(scope)
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
  val id = UUID.randomUUID().toString()
  val message = Message(id, scope, "user", content, delivery = DeliveryStatus.PENDING, requestId = id)
  try { dao.insert(message) } catch (e: Exception) {
   if (e is CancellationException) throw e
   throw MessageNotSavedException(e)
  }
  deliver(message)
 }
 suspend override fun retry(id: String, newRequest: Boolean) = chatMutex.withLock {
  val message = requireNotNull(dao.message(scope, id)) { "This message is no longer in the current workspace." }
  require(message.role == "user")
  if (message.delivery == DeliveryStatus.SENT) return@withLock
  if (newRequest) require(message.delivery == DeliveryStatus.FAILED) { "Check for the existing reply first." }
  else require(message.delivery == DeliveryStatus.RETRYABLE) { "This request requires confirmation before sending again." }
  val pending = message.copy(
   delivery = DeliveryStatus.PENDING, deliveryError = null,
   requestId = if (newRequest) UUID.randomUUID().toString() else message.requestId.ifBlank { message.id }
  )
  dao.insert(pending)
  deliver(pending)
 }
 private suspend fun deliver(message: Message) {
  val remote = api
  try {
   // Only explicit demo mode generates a local reply. Network failures never fall back to demo.
   val reply = if (message.scope == "demo" && remote == null) {
    "This is a demo conversation. Connect your Atlas server to receive real AI replies."
   } else {
    checkNotNull(remote) { "Connect to your Atlas server first." }
    remote.chat(ChatRequest(message.text, "android-${message.scope}", message.requestId.ifBlank { message.id })).reply
   }
   if (reply.isNullOrBlank()) throw InvalidReplyException()
   dao.complete(message, Message("${message.id}-reply", message.scope, "assistant", reply, createdAt = maxOf(System.currentTimeMillis(), message.createdAt + 1)))
  } catch (e: Exception) {
   val state = if (e is HttpException && e.code() in setOf(401, 403, 404, 409, 422, 429, 502, 504)) DeliveryStatus.FAILED else DeliveryStatus.RETRYABLE
   withContext(NonCancellable) {
    dao.insert(message.copy(delivery = state, deliveryError = if(e is CancellationException) "Reply interrupted. Check for the reply." else ChatErrors.message(e)))
   }
   throw e
  }
 }
 suspend override fun remember(section: String, fact: String) {
  val remote = api
  if (remote == null) dao.insertMemories(listOf(Memory(scope, UUID.randomUUID().toString(), section, fact)))
  else { remote.remember(MemoryRequest(section, fact)); refreshMemory() }
 }
 suspend override fun profile() = api?.agent() ?: AgentProfile(content = "I’m Atlas, your personal AI companion. I help with projects, learning, and automation.\n\nPersonality\nHelpful, honest, concise, and practical.\n\nDemo profile — the live identity will come from agent.md.")
 suspend override fun files() = api?.files() ?: listOf(FileItem("agent.md", "agent.md", false, 1254), FileItem("memory.md", "memory.md", false, 68), FileItem("backups", "backups", true))
 suspend override fun health() = api?.health() ?: Health("demo", "Preview data", 0)
 suspend override fun clearChat() = dao.clearMessages(scope)
}
