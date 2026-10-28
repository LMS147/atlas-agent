package com.atlas.ai.chat

import com.atlas.ai.core.database.AtlasDao
import com.atlas.ai.core.network.ApiFactory
import com.atlas.ai.data.local.*
import com.atlas.ai.data.repository.DefaultAtlasRepository
import com.atlas.ai.domain.model.DeliveryStatus
import com.google.gson.JsonParser
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import okhttp3.mockwebserver.SocketPolicy
import okhttp3.tls.HandshakeCertificates
import okhttp3.tls.HeldCertificate
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.util.UUID
import java.util.concurrent.LinkedBlockingQueue

class RealChatTest {
 private lateinit var server: MockWebServer
 private lateinit var client: OkHttpClient
 private lateinit var dao: FakeDao
 private lateinit var repo: DefaultAtlasRepository
 private val token = "atlas-android-test-" + "x".repeat(32)
 private val requests = LinkedBlockingQueue<RecordedRequest>()
 private val responses = LinkedBlockingQueue<MockResponse>()
 private var healthStatus = 200

 @Before fun setup() {
  val certificate = HeldCertificate.Builder().addSubjectAlternativeName("localhost").build()
  val serverCertificates = HandshakeCertificates.Builder().heldCertificate(certificate).build()
  val clientCertificates = HandshakeCertificates.Builder().addTrustedCertificate(certificate.certificate).build()
  client = OkHttpClient.Builder().sslSocketFactory(clientCertificates.sslSocketFactory(), clientCertificates.trustManager)
   .protocols(listOf(Protocol.HTTP_1_1)).build()
  server = MockWebServer()
  server.useHttps(serverCertificates.sslSocketFactory(), false)
  server.dispatcher = object : Dispatcher() {
   override fun dispatch(request: RecordedRequest): MockResponse {
    requests.offer(request)
    return if(request.path == "/api/v1/health") json("""{"status":"ok","version":"0.2.0","uptime_seconds":2}""", healthStatus)
    else responses.poll() ?: json("""{"reply":"A real server reply"}""")
   }
  }
  server.start()
  dao = FakeDao()
  repo = newRepository()
 }
 private fun newRepository() = DefaultAtlasRepository(dao) { url, credential -> ApiFactory.create(url, credential, client) }
 private fun json(body: String, status: Int = 200) = MockResponse().setResponseCode(status).setHeader("Content-Type", "application/json").setBody(body)
 private fun requestBody(request: RecordedRequest) = JsonParser.parseString(request.body.readUtf8()).asJsonObject
 private suspend fun connect() = repo.connect(server.url("/").toString(), token)
 @After fun shutdown() { server.shutdown(); client.connectionPool.evictAll(); client.dispatcher.executorService.shutdown() }

 @Test fun authenticatedHttpsChatCachesOnlyActualReply() = runBlocking {
  connect()
  repo.send("Hello Atlas")
  val health = requests.remove()
  val chat = requests.remove()
  assertEquals("/api/v1/health", health.path)
  assertEquals("Bearer $token", health.getHeader("Authorization"))
  assertEquals("/api/v1/chat", chat.path)
  assertEquals("Bearer $token", chat.getHeader("Authorization"))
  val body = requestBody(chat)
  assertEquals("Hello Atlas", body["message"].asString)
  assertEquals("android-${repo.scope}", body["conversation_id"].asString)
  UUID.fromString(body["request_id"].asString)
  val rows = repo.messages().first()
  assertEquals(listOf("user", "assistant"), rows.map { it.role })
  assertEquals("A real server reply", rows.last().text)
  assertEquals(DeliveryStatus.SENT, rows.first().delivery)
  assertFalse(repo.demo)
 }

 @Test fun droppedReplyIsRecoveredWithSameRequestAndNoDuplicateBubble() = runBlocking {
  connect(); requests.clear()
  responses.offer(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AFTER_REQUEST))
  try { repo.send("Remember this") ; fail("Expected interrupted transport") } catch (_: java.io.IOException) {}
  val original = requestBody(requests.remove())
  val pending = repo.messages().first().single()
  assertEquals(DeliveryStatus.RETRYABLE, pending.delivery)
  assertFalse(repo.demo)
  responses.offer(json("""{"reply":"Cached reply from Atlas"}"""))
  repo.retry(pending.id, false)
  val replay = requestBody(requests.remove())
  assertEquals(original["request_id"].asString, replay["request_id"].asString)
  assertEquals(original["conversation_id"].asString, replay["conversation_id"].asString)
  val rows = repo.messages().first()
  assertEquals(1, rows.count { it.role == "user" })
  assertEquals(1, rows.count { it.role == "assistant" })
  assertEquals("Cached reply from Atlas", rows.last().text)
  repo.retry(pending.id, false)
  assertTrue(requests.isEmpty())
 }

 @Test fun explicitFailureRequiresConfirmationAndNewRequestId() = runBlocking {
  connect(); requests.clear()
  responses.offer(json("""{"detail":"incomplete request"}""", 409))
  try { repo.send("A message"); fail("Expected conflict") } catch (e: retrofit2.HttpException) { assertEquals(409, e.code()) }
  val original = requestBody(requests.remove())
  val failed = repo.messages().first().single()
  assertEquals(DeliveryStatus.FAILED, failed.delivery)
  try { repo.retry(failed.id, false); fail("Must require explicit new request") } catch (_: IllegalArgumentException) {}
  assertTrue(requests.isEmpty())
  repo.retry(failed.id, true)
  val resend = requestBody(requests.remove())
  assertNotEquals(original["request_id"].asString, resend["request_id"].asString)
  assertEquals(1, repo.messages().first().count { it.role == "user" })
 }

 @Test fun reopenedAppRecoversPendingStateWithoutAutomaticallyPosting() = runBlocking {
  connect(); requests.clear()
  val id = UUID.randomUUID().toString()
  dao.insert(Message(id, repo.scope, "user", "Pending turn", delivery = DeliveryStatus.PENDING, requestId = id))
  repo = newRepository()
  connect()
  assertEquals(listOf("/api/v1/health"), requests.toList().map { it.path })
  requests.clear()
  assertEquals(DeliveryStatus.RETRYABLE, repo.messages().first().single().delivery)
  repo.retry(id, false)
  assertEquals(id, requestBody(requests.remove())["request_id"].asString)
 }

 @Test fun credentialsAndDemoUseSeparateCachesAndFailedConnectKeepsWorkspace() = runBlocking {
  repo.useDemo(); repo.send("Demo only")
  assertTrue(requests.isEmpty())
  assertTrue(repo.messages().first().last().text.contains("demo"))
  connect(); repo.send("Server only")
  assertFalse(repo.messages().first().any { it.text == "Demo only" })
  val originalScope = repo.scope
  healthStatus = 401
  try { repo.connect(server.url("/").toString(), "different-token"); fail("Expected unauthorized") } catch (_: retrofit2.HttpException) {}
  assertEquals(originalScope, repo.scope)
  assertFalse(repo.demo)
  healthStatus = 200
  repo.connect(server.url("/").toString(), "different-token")
  assertTrue(repo.messages().first().isEmpty())
 }

 @Test fun blankProviderReplyAndInvalidInputNeverCreateFakeReplies() = runBlocking {
  connect(); requests.clear()
  responses.offer(json("""{"reply":""}"""))
  try { repo.send("A valid request"); fail("Expected invalid reply") } catch (_: com.atlas.ai.core.network.InvalidReplyException) {}
  assertEquals(DeliveryStatus.RETRYABLE, repo.messages().first().single().delivery)
  val previousCount = repo.messages().first().size
  for(text in listOf(" ", "x".repeat(8001))) {
   try { repo.send(text); fail("Invalid message must be rejected") } catch (_: IllegalArgumentException) {}
  }
  assertEquals(previousCount, repo.messages().first().size)
 }
}

private class FakeDao : AtlasDao {
 private val rows = linkedMapOf<String, Message>()
 private val updates = MutableStateFlow<List<Message>>(emptyList())
 private val memoryUpdates = MutableStateFlow<List<Memory>>(emptyList())
 override fun messages(scope: String): Flow<List<Message>> = updates.map { list -> list.filter { it.scope == scope }.sortedBy { it.createdAt } }
 override suspend fun insert(message: Message) { rows[message.id] = message; updates.value = rows.values.toList() }
 override suspend fun message(scope: String, id: String) = rows[id]?.takeIf { it.scope == scope }
 override suspend fun recoverInterrupted(scope: String) {
  rows.values.filter { it.scope == scope && it.delivery == DeliveryStatus.PENDING }.toList().forEach {
   insert(it.copy(delivery = DeliveryStatus.RETRYABLE, deliveryError = "App interrupted"))
  }
 }
 override fun memories(scope: String): Flow<List<Memory>> = memoryUpdates.map { list -> list.filter { it.scope == scope } }
 override suspend fun memoryCount(scope: String) = memoryUpdates.value.count { it.scope == scope }
 override suspend fun clearMemories(scope: String) { memoryUpdates.value = memoryUpdates.value.filterNot { it.scope == scope } }
 override suspend fun insertMemories(items: List<Memory>) { memoryUpdates.value = memoryUpdates.value + items }
 override suspend fun clearMessages(scope: String) { rows.values.filter { it.scope == scope }.map { it.id }.forEach { rows.remove(it) }; updates.value = rows.values.toList() }
}
