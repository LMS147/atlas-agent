package com.atlas.ai.domain.model

import com.atlas.ai.data.local.*
import com.atlas.ai.data.model.*

data class UiState(
 val screen: String = "Welcome", val demo: Boolean = true, val busy: Boolean = false,
 val error: String? = null, val messages: List<Message> = emptyList(), val memories: List<Memory> = emptyList(),
 val profile: AgentProfile = AgentProfile(), val files: List<FileItem> = emptyList(), val health: Health? = null,
 val timestamps: Boolean = true, val serverUrl: String = "",
 val conversations: List<Conversation> = emptyList(), val activeConversation: Conversation? = null,
 val connectionStatus: String = "Not connected", val restoredDraft: String? = null
)
