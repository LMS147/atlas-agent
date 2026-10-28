package com.atlas.ai.domain.repository

import com.atlas.ai.data.local.Message
import com.atlas.ai.data.local.Memory
import com.atlas.ai.data.model.*
import kotlinx.coroutines.flow.Flow

/** Application-facing contract. DTO/entity separation can expand with the backend. */
interface AtlasRepository {
 val scope: String
 val demo: Boolean
 fun messages(): Flow<List<Message>>
 fun memories(): Flow<List<Memory>>
 fun useDemo()
 suspend fun connect(url: String, token: String)
 suspend fun seed()
 suspend fun refreshMemory()
 suspend fun send(text: String)
 suspend fun retry(id: String, newRequest: Boolean = false)
 suspend fun remember(section: String, fact: String)
 suspend fun profile(): AgentProfile
 suspend fun files(): List<FileItem>
 suspend fun health(): Health
 suspend fun clearChat()
}
