package com.atlas.ai.data.model

data class Health(val status: String, val version: String = "", val uptime_seconds: Long = 0)
data class ChatRequest(val message: String, val conversation_id: String, val request_id: String, val require_existing: Boolean = true)
data class ChatReply(val reply: String)
data class MemoryItem(val id: String, val section: String, val fact: String)
data class MemoryRequest(val section: String, val fact: String)
data class AgentProfile(val name: String = "Atlas", val content: String = "")
data class FileItem(val name: String, val path: String, val directory: Boolean, val size_bytes: Long = 0, val writable: Boolean = false)

data class ConversationDto(val id: String, val title: String, val created_at: Long, val updated_at: Long, val message_count: Int, val preview: String, val deleted: Boolean = false)
data class ConversationName(val title: String = "New chat")
data class TranscriptDto(val seq: Long, val id: String, val request_id: String, val role: String, val text: String, val created_at: Long)
data class MessagePage(val items: List<TranscriptDto>, val has_more: Boolean, val next_before: Long?)

data class ChatRequestStatus(val request_id: String, val status: String, val reply: String?)


data class FileDocument(val path: String, val content: String, val revision: String, val writable: Boolean)
data class FileEdit(val content: String, val revision: String)
data class CompactPlan(val revision: String, val before_chars: Int, val after_chars: Int, val removed_entries: Int)
data class CompactRequest(val revision: String)
data class RamMetrics(val total_bytes: Long, val available_bytes: Long, val used_bytes: Long)
data class StorageMetrics(val total_bytes: Long, val used_bytes: Long, val free_bytes: Long)
data class ServiceMetrics(val pid: Int, val uptime_seconds: Long, val threads: Int, val requests: Long, val errors: Long, val active_requests: Int)
data class Monitoring(val sampled_at: Long, val device_cpu_percent: Double?, val process_cpu_percent: Double,
 val ram: RamMetrics?, val process_rss_bytes: Long?, val storage: StorageMetrics?, val device_uptime_seconds: Long?,
 val service: ServiceMetrics, val unavailable: List<String>)
