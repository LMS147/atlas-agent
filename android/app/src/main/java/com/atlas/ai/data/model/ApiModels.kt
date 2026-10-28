package com.atlas.ai.data.model

data class Health(val status: String, val version: String = "", val uptime_seconds: Long = 0)
data class ChatRequest(val message: String, val conversation_id: String, val request_id: String)
data class ChatReply(val reply: String)
data class MemoryItem(val id: String, val section: String, val fact: String)
data class MemoryRequest(val section: String, val fact: String)
data class AgentProfile(val name: String = "Atlas", val content: String = "")
data class FileItem(val name: String, val path: String, val directory: Boolean, val size_bytes: Long = 0)
