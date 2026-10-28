package com.atlas.ai.navigation

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.room.Room
import com.atlas.ai.core.network.ApiFactory
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
 private val db = Room.databaseBuilder(app, AtlasDatabase::class.java, "atlas.db").build()
 private val repo: AtlasRepository = DefaultAtlasRepository(db.dao())
 private val sendMessage = SendMessage(repo)
 private val secure = SecureStore(app)
 private val _state = MutableStateFlow(UiState())
 val state = _state.asStateFlow()
 private var messagesJob: Job? = null
 private var memoryJob: Job? = null
 init { viewModelScope.launch { try { secure.load()?.let { connect(it.first, it.second, true) } } catch (e: Exception) { _state.update { it.copy(screen = "Server setup", error = "Saved credentials could not be restored. Enter them again.") } } } }
 private fun observe() {
  messagesJob?.cancel(); memoryJob?.cancel()
  _state.update { it.copy(messages = emptyList(), memories = emptyList(), profile = AgentProfile(), files = emptyList(), health = null) }
  messagesJob = viewModelScope.launch { repo.messages().collect { rows -> _state.update { it.copy(messages = rows) } } }
  memoryJob = viewModelScope.launch { repo.memories().collect { rows -> _state.update { it.copy(memories = rows) } } }
 }
 private fun task(block: suspend () -> Unit) {
  if (_state.value.busy) return
  viewModelScope.launch {
   _state.update { it.copy(busy = true, error = null) }
   try { block() } catch (e: CancellationException) { throw e } catch (e: Exception) {
    val message = when (e) { is HttpException -> "Server returned HTTP ${e.code()}. Check the API and access token."; is java.io.IOException -> "Cannot reach Atlas. Check your connection and tunnel, then try again."; is IllegalArgumentException -> e.message ?: "Check the supplied values."; else -> "The operation failed. Check server compatibility and try again." }
    _state.update { it.copy(error = message) }
   } finally { _state.update { it.copy(busy = false) } }
  }
 }
 fun demo() = task { repo.useDemo(); observe(); repo.seed(); _state.update { it.copy(screen = "Chat", demo = true) } }
 fun connect(url: String, token: String, remember: Boolean) = task {
  val normalized = ApiFactory.normalize(url)
  repo.connect(normalized, token.trim())
  observe()
  _state.update { it.copy(screen = "Chat", demo = false) }
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
 fun send(text: String) { if (text.isNotBlank()) task { sendMessage(text) } }
 fun remember(section: String, fact: String) { if (fact.isNotBlank()) task { repo.remember(section, fact.trim().take(300)) } }
 fun clearChat() = task { repo.clearChat() }
 fun toggleTimestamps() { _state.update { it.copy(timestamps = !it.timestamps) } }
 fun disconnect() = task { secure.clear(); repo.useDemo(); messagesJob?.cancel(); memoryJob?.cancel(); _state.value = UiState(screen = "Server setup", busy = true) }
 override fun onCleared() { super.onCleared(); db.close() }
}
