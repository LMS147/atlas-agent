package com.atlas.ai.data.local

import androidx.room.*

@Entity(tableName = "messages")
data class Message(@PrimaryKey val id: String, val scope: String, val role: String, val text: String, val createdAt: Long = System.currentTimeMillis())
@Entity(tableName = "memories", primaryKeys = ["scope", "id"])
data class Memory(val scope: String, val id: String, val section: String, val fact: String)
