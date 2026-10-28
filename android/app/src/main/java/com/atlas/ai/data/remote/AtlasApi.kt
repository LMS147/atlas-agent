package com.atlas.ai.data.remote

import retrofit2.http.*
import com.atlas.ai.data.model.*

interface AtlasApi {
 @GET("api/v1/health") suspend fun health(): Health
 @POST("api/v1/chat") suspend fun chat(@Body request: ChatRequest): ChatReply
 @GET("api/v1/memory") suspend fun memories(): List<MemoryItem>
 @POST("api/v1/memory") suspend fun remember(@Body request: MemoryRequest): MemoryItem
 @GET("api/v1/agent") suspend fun agent(): AgentProfile
 @GET("api/v1/files") suspend fun files(): List<FileItem>
}
