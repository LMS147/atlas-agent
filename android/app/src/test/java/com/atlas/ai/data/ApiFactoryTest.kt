package com.atlas.ai.data

import com.atlas.ai.core.network.ApiFactory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ApiFactoryTest {
 @Test fun normalizesHttpsBasePath() {
  assertEquals("https://atlas.example.com/service/", ApiFactory.normalize(" https://atlas.example.com/service "))
 }
 @Test fun rejectsInsecureOrCredentialBearingUrls() {
  listOf("http://atlas.example.com", "https://user:secret@atlas.example.com", "https://atlas.example.com?token=secret", "https://atlas.example.com/#fragment", "invalid").forEach { value ->
   assertThrows(IllegalArgumentException::class.java) { ApiFactory.normalize(value) }
  }
 }
 @Test fun rejectsBlankOrMultilineTokens() {
  listOf("", "secret\r\nInjected: value").forEach { token ->
   assertThrows(IllegalArgumentException::class.java) { ApiFactory.create("https://atlas.example.com/", token) }
  }
 }
}
