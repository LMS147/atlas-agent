package com.atlas.ai.domain.model

object DeliveryStatus {
 const val SENT = "sent"
 const val PENDING = "pending"
 const val RETRYABLE = "retryable"
 const val UNCONFIRMED = "not_received"
 const val FAILED = "failed"
}
