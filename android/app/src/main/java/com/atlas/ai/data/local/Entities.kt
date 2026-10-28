package com.atlas.ai.data.local

import androidx.room.*
import com.atlas.ai.domain.model.DeliveryStatus

@Entity(tableName = "messages")
data class Message(@PrimaryKey val id: String, val scope: String, val role: String, val text: String, val createdAt: Long = System.currentTimeMillis(),
 @ColumnInfo(defaultValue = "'sent'") val delivery: String = DeliveryStatus.SENT,
 @ColumnInfo(defaultValue = "''") val requestId: String = "",
 @ColumnInfo(defaultValue = "NULL") val deliveryError: String? = null
)
@Entity(tableName = "memories", primaryKeys = ["scope", "id"])
data class Memory(val scope: String, val id: String, val section: String, val fact: String)
