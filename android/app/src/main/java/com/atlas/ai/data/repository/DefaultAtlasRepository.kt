package com.atlas.ai.data.repository

import com.atlas.ai.core.database.AtlasDao
import com.atlas.ai.core.network.ApiFactory
import com.atlas.ai.data.local.*
import com.atlas.ai.data.model.*
import com.atlas.ai.data.remote.AtlasApi
import com.atlas.ai.domain.repository.AtlasRepository

import java.util.UUID

class DefaultAtlasRepository(private val dao: AtlasDao) : AtlasRepository {
 override var scope: String = "demo"; private set
 private var api: AtlasApi? = null
 override val demo get() = api == null
 override fun messages() = dao.messages(scope)
 override fun memories() = dao.memories(scope)
 override fun useDemo() { api = null; scope = "demo" }
 suspend override fun connect(url: String, token: String) {
  val candidate = ApiFactory.create(url, token)
  require(candidate.health().status == "ok") { "Server is not ready" }
  api = candidate
  // Separate server and credential identities to prevent account cache crossover.
  val hash = java.security.MessageDigest.getInstance("SHA-256").digest((url + "\n" + token).toByteArray())
  scope = hash.joinToString("") { "%02x".format(it) }
 }
 suspend override fun seed() {
  if (demo && dao.memoryCount(scope) == 0) dao.replaceMemories(scope, listOf(
   Memory(scope, "1", "Projects", "Build the Atlas Android companion with Kotlin and Jetpack Compose."),
   Memory(scope, "2", "User Preferences", "Keep replies helpful, honest, concise, and practical."),
   Memory(scope, "3", "Decisions", "The Groq API key stays on the Python server.")
  ))
 }
 suspend override fun refreshMemory() { api?.let { remote -> dao.replaceMemories(scope, remote.memories().map { Memory(scope, it.id, it.section, it.fact) }) } }
 suspend override fun send(text: String) {
  val id = UUID.randomUUID().toString()
  dao.insert(Message(id, scope, "user", text))
  val reply = api?.chat(ChatRequest(text, "android-$scope", id))?.reply
   ?: "This is a demo conversation. Your message is saved on this device. Connect your Atlas API in Server setup to receive real AI replies."
  dao.insert(Message(UUID.randomUUID().toString(), scope, "assistant", reply))
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
