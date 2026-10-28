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
 private val db = Room.databaseBuilder(app, AtlasDatabase::class.java, "atlas.db").addMigrations(AtlasDatabase.MIGRATION_1_2).build()
 private val repo: AtlasRepository = DefaultAtlasRepository(db.dao())
 private val sendMessage = SendMessage(repo)
 private val secure = SecureStore(app)
 private val _state = MutableStateFlow(UiState())
 val state = _state.asStateFlow()
 private var messagesJob: Job? = null
 private var memoryJob: Job? = null
 init { viewModelScope.launch { try { secure.load()?.let { saved -> _state.update { it.copy(screen = "Server setup", serverUrl = saved.first) }; connect(saved.first, saved.second, true) } } catch (e: Exception) { _state.update { it.copy(screen = "Server setup", error = "Saved credentials could not be restored. Enter them again.") } } } }
 private fun observe() {
  messagesJob?.cancel(); memoryJob?.cancel()
  _state.update { it.copy(messages = emptyList(), memories = emptyList(), profile = AgentProfile(), files = emptyList(), health = null) }
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
 fun demo() = task { repo.useDemo(); observe(); repo.seed(); _state.update { it.copy(screen = "Chat", demo = true, connectionStatus = "Demo mode", serverUrl = "") } }
 fun connect(url: String, token: String, remember: Boolean) = task {
  val normalized = ApiFactory.normalize(url)
  repo.connect(normalized, token.trim())
  observe()
  _state.update { it.copy(screen = "Chat", demo = false, serverUrl = normalized, connectionStatus = "Connected · HTTPS") }
  if (remember) secure.save(normalized, token.trim()) else secure.clear()
 }
 fun navigate(screen: String) {
  if (_state.value.busy) return
  _state.update { it.copy(screen = screen, error = null) }
  when(screen) {
   "Memory" -> task { repo.refreshMemory() }
   "Agent profile" -> task { val profile = repo.profile(); _state.update { it.copy(profile = profile) } }
   "Files" -> task { val files = repo.files(); _state.update { it.copy(files = files) } }
   "Server status" -> task { val health = repo.health(); _state.update { it.copy(health = health) } }
  }
 }
 fun send(text: String): Boolean {
  if (_state.value.busy || text.isBlank() || text.trim().length > 8000) return false
  if (_state.value.messages.any { it.role == "user" && it.delivery == com.atlas.ai.domain.model.DeliveryStatus.RETRYABLE }) return false
  task(draft = text) { sendMessage(text); _state.update { it.copy(connectionStatus = if(it.demo) "Demo mode" else "Connected · HTTPS") } }
  return true
 }
 fun retry(id: String, newRequest: Boolean = false) = task {
  repo.retry(id, newRequest)
  _state.update { it.copy(connectionStatus = if(it.demo) "Demo mode" else "Connected · HTTPS") }
 }
 fun consumeRestoredDraft() { _state.update { it.copy(restoredDraft = null) } }
 fun remember(section: String, fact: String) { if (fact.isNotBlank()) task { repo.remember(section, fact.trim().take(300)) } }
 fun clearChat() = task { repo.clearChat() }
 fun toggleTimestamps() { _state.update { it.copy(timestamps = !it.timestamps) } }
 fun disconnect() = task { secure.clear(); repo.useDemo(); messagesJob?.cancel(); memoryJob?.cancel(); _state.value = UiState(screen = "Server setup", busy = true) }
 override fun onCleared() { super.onCleared(); db.close() }
}
