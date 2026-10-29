package com.atlas.ai.navigation

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.room.Room
import com.atlas.ai.core.network.*
import com.atlas.ai.core.database.AtlasDatabase
import com.atlas.ai.core.security.SecureStore
import com.atlas.ai.data.repository.DefaultAtlasRepository
import com.atlas.ai.domain.model.UiState
import com.atlas.ai.domain.repository.AtlasRepository
import com.atlas.ai.domain.usecase.SendMessage
import com.atlas.ai.data.model.AgentProfile
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import retrofit2.HttpException

class AtlasViewModel(app: Application) : AndroidViewModel(app) {
 private val db = AtlasDatabase.getInstance(app)
 private val repo: AtlasRepository = DefaultAtlasRepository(db.dao())
 private val sendMessage = SendMessage(repo)
 private val secure = SecureStore(app)
 private val _state = MutableStateFlow(UiState())
 val state = _state.asStateFlow()
 private var messagesJob: Job? = null
 private var memoryJob: Job? = null
 private var conversationsJob: Job? = null
 init { viewModelScope.launch { try { secure.load()?.let { saved -> _state.update { it.copy(screen = "Server setup", serverUrl = saved.first) }; connect(saved.first, saved.second, true) } } catch (e: Exception) { _state.update { it.copy(screen = "Server setup", error = "Saved credentials could not be restored. Enter them again.") } } } }
 private fun observe() {
  messagesJob?.cancel(); memoryJob?.cancel(); conversationsJob?.cancel()
  _state.update { it.copy(messages = emptyList(), memories = emptyList(), profile = AgentProfile(), files = emptyList(), health = null, conversations = emptyList(), activeConversation = null) }
  conversationsJob = viewModelScope.launch { repo.conversations().collect { rows -> _state.update { it.copy(conversations=rows,activeConversation=rows.firstOrNull { row -> row.id == repo.conversationId }) } } }
  messagesJob = viewModelScope.launch { repo.messages().collect { rows -> _state.update { it.copy(messages = rows) } } }
  memoryJob = viewModelScope.launch { repo.memories().collect { rows -> _state.update { it.copy(memories = rows) } } }
 }
 private fun task(draft: String? = null, block: suspend () -> Unit) {
  if (_state.value.busy) return
  _state.update { it.copy(busy = true, error = null, restoredDraft = null) }
  viewModelScope.launch {
   try { block() } catch (e: CancellationException) { throw e } catch (e: Exception) {
    _state.update { it.copy(
     error = ChatErrors.message(e),
     restoredDraft = if (e is MessageNotSavedException) draft else null,
     connectionStatus = if(e is java.io.IOException) "Connection issue" else if(e is HttpException && e.code() == 401) "Authentication required" else it.connectionStatus
    ) }
   } finally { _state.update { it.copy(busy = false) } }
  }
 }
 fun demo() = task { repo.useDemo(); repo.seed(); observe(); _state.update { it.copy(screen = "Chat", demo = true, connectionStatus = "Demo mode", serverUrl = "") } }
 fun connect(url: String, token: String, remember: Boolean) = task {
  val normalized = ApiFactory.normalize(url)
  repo.connect(normalized, token.trim())
  observe()
  _state.update { it.copy(screen = "Chat", demo = false, serverUrl = normalized, connectionStatus = if(repo.offline) "Offline · cached chats" else "Connected · HTTPS") }
  if (!repo.offline) repo.refreshHistory()
  if (remember) secure.save(normalized, token.trim()) else secure.clear()
 }
 fun navigate(screen: String) {
  if (_state.value.busy) return
  _state.update { it.copy(screen = screen, error = null) }
  when(screen) {
   "Conversations" -> task { repo.refreshConversations(); observe(); connectionStatus() }
   "Memory" -> task { repo.refreshMemory() }
   "Agent profile" -> task { val profile = repo.profile(); _state.update { it.copy(profile = profile) } }
   "Files" -> task { val files = repo.files(); _state.update { it.copy(files = files) } }
   "Server status" -> task { val health = repo.health(); _state.update { it.copy(health = health) } }
  }
 }
 fun send(text: String): Boolean {
  if (_state.value.activeConversation == null || _state.value.activeConversation?.serverAvailable == false) return false
  if (_state.value.busy || text.isBlank() || text.trim().length > 8000) return false
  if (_state.value.messages.any { it.role == "user" && it.delivery in setOf(com.atlas.ai.domain.model.DeliveryStatus.RETRYABLE,com.atlas.ai.domain.model.DeliveryStatus.UNCONFIRMED) }) return false
  task(draft = text) { sendMessage(text); _state.update { it.copy(connectionStatus = if(it.demo) "Demo mode" else "Connected · HTTPS") } }
  return true
 }
 fun recover(id: String) = task { repo.recover(id); connectionStatus() }
 fun retry(id: String, newRequest: Boolean = false) = task {
  repo.retry(id, newRequest)
  _state.update { it.copy(connectionStatus = if(it.demo) "Demo mode" else "Connected · HTTPS") }
 }
 private fun connectionStatus() { _state.update { it.copy(connectionStatus=if(repo.demo) "Demo mode" else if(repo.offline) "Offline · cached chats" else "Connected · HTTPS") } }
 fun newConversation() = task {
  repo.newConversation()
  connectionStatus()
  observe()
  _state.update { it.copy(screen="Chat") }
 }
 fun openConversation(id: String) = task {
  repo.selectConversation(id)
  observe()
  _state.update { it.copy(screen="Chat") }
  repo.refreshHistory()
  connectionStatus()
 }
 fun renameConversation(id: String,title: String) = task { repo.renameConversation(id,title) }
 fun deleteConversation(id: String) = task { repo.deleteConversation(id); observe() }
 fun loadEarlier() = task { repo.refreshHistory(earlier=true); connectionStatus() }
 fun refreshChat() = task { repo.refreshHistory(); connectionStatus() }
 fun consumeRestoredDraft() { _state.update { it.copy(restoredDraft = null) } }
 fun remember(section: String, fact: String) { if (fact.isNotBlank()) task { repo.remember(section, fact.trim().take(300)) } }
 fun clearChat() = task { repo.clearChat() }
 fun toggleTimestamps() { _state.update { it.copy(timestamps = !it.timestamps) } }
 fun disconnect() = task { secure.clear(); repo.useDemo(); messagesJob?.cancel(); memoryJob?.cancel(); conversationsJob?.cancel(); _state.value = UiState(screen = "Server setup", busy = true) }
}
