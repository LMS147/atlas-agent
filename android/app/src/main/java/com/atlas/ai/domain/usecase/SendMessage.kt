package com.atlas.ai.domain.usecase

import com.atlas.ai.domain.repository.AtlasRepository

class SendMessage(private val repository: AtlasRepository) {
 suspend operator fun invoke(text: String) {
  require(text.isNotBlank()) { "Message cannot be empty" }
  repository.send(text.trim())
 }
}
