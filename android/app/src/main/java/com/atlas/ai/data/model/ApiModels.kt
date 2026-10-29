package com.atlas.ai.data.model

data class Health(val status: String, val version: String = "", val uptime_seconds: Long = 0)
data class ChatRequest(val message: String, val conversation_id: String, val request_id: String, val require_existing: Boolean = true)
data class ChatReply(val reply: String)
data class MemoryItem(val id: String, val section: String, val fact: String)
data class MemoryRequest(val section: String, val fact: String)
data class AgentProfile(val name: String = "Atlas", val content: String = "")
data class FileItem(val name: String, val path: String, val directory: Boolean, val size_bytes: Long = 0)

data class ConversationDto(val id: String, val title: String, val created_at: Long, val updated_at: Long, val message_count: Int, val preview: String, val deleted: Boolean = false)
data class ConversationName(val title: String = "New chat")
data class TranscriptDto(val seq: Long, val id: String, val request_id: String, val role: String, val text: String, val created_at: Long)
data class MessagePage(val items: List<TranscriptDto>, val has_more: Boolean, val next_before: Long?)

data class ChatRequestStatus(val request_id: String, val status: String, val reply: String?)
