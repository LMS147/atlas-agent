package com.atlas.ai.data.remote

import retrofit2.http.*
import com.atlas.ai.data.model.*

interface AtlasApi {
 @GET("api/v1/conversations") suspend fun conversations(@Query("include_deleted") includeDeleted: Boolean = true): List<ConversationDto>
 @POST("api/v1/conversations") suspend fun createConversation(@Body name: ConversationName): ConversationDto
 @GET("api/v1/conversations/{id}") suspend fun conversation(@Path("id") id: String): ConversationDto
 @PATCH("api/v1/conversations/{id}") suspend fun renameConversation(@Path("id") id: String, @Body name: ConversationName): ConversationDto
 @DELETE("api/v1/conversations/{id}") suspend fun deleteConversation(@Path("id") id: String)
 @GET("api/v1/conversations/{id}/messages") suspend fun history(@Path("id") id: String, @Query("before") before: Long? = null, @Query("limit") limit: Int = 50): MessagePage
 @GET("api/v1/health") suspend fun health(): Health
 @POST("api/v1/chat") suspend fun chat(@Body request: ChatRequest): ChatReply
 @GET("api/v1/memory") suspend fun memories(): List<MemoryItem>
 @POST("api/v1/memory") suspend fun remember(@Body request: MemoryRequest): MemoryItem
 @GET("api/v1/agent") suspend fun agent(): AgentProfile
 @GET("api/v1/files") suspend fun files(): List<FileItem>
}
