package com.atlas.ai.chat

import com.atlas.ai.core.network.ApiFactory
import com.atlas.ai.data.local.*
import com.atlas.ai.data.model.*
import com.atlas.ai.data.repository.DefaultAtlasRepository
import com.atlas.ai.domain.model.DeliveryStatus
import com.google.gson.Gson
import com.google.gson.JsonParser
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.mockwebserver.*
import okhttp3.tls.HandshakeCertificates
import okhttp3.tls.HeldCertificate
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.util.UUID
import java.util.concurrent.LinkedBlockingQueue

class RealChatTest {
 private lateinit var server:MockWebServer
 private lateinit var client:OkHttpClient
 private lateinit var dao:FakeDao
 private lateinit var repo:DefaultAtlasRepository
 private val token="atlas-android-test-"+"x".repeat(32)
 private val requests=LinkedBlockingQueue<RecordedRequest>()
 private val responses=LinkedBlockingQueue<MockResponse>()
 private val metadata=linkedMapOf<String,ConversationDto>()
 private val transcript=mutableMapOf<String,MutableList<TranscriptDto>>()
 private var sequence=0L
 private val requestStates=mutableMapOf<String,String>()
 private var disconnectStatus=false
 private var healthStatus=200
 private var stopped=false
 private val gson=Gson()

 @Before fun setup() {
  val cert=HeldCertificate.Builder().addSubjectAlternativeName("localhost").build()
  val serverCerts=HandshakeCertificates.Builder().heldCertificate(cert).build()
  val trust=HandshakeCertificates.Builder().addTrustedCertificate(cert.certificate).build()
  client=OkHttpClient.Builder().sslSocketFactory(trust.sslSocketFactory(),trust.trustManager).protocols(listOf(Protocol.HTTP_1_1)).build()
  server=MockWebServer(); server.useHttps(serverCerts.sslSocketFactory(),false)
  metadata["test-conversation"]=ConversationDto("test-conversation","Test chat",1,1,0,"")
  server.dispatcher=object:Dispatcher() {
   override fun dispatch(request:RecordedRequest):MockResponse {
    requests.offer(request)
    val path=request.path!!.substringBefore('?')
    if(path=="/api/v1/health") return json(mapOf("status" to "ok","version" to "0.3.0","uptime_seconds" to 2),healthStatus)
    if(path=="/api/v1/conversations") {
     if(request.method=="POST") {
      val id="chat-${UUID.randomUUID()}"
      val item=ConversationDto(id,body(request)["title"].asString,2,2,0,"")
      metadata[id]=item
      return json(item,201)
     }
     return json(metadata.values.toList())
    }
    if(path=="/api/v1/chat") {
     val payload=body(request)
     val id=payload["conversation_id"].asString
     val requestId=payload["request_id"].asString
     if(payload["require_existing"].asBoolean && metadata[id]==null) return json(mapOf("detail" to "missing"),404)
     if(metadata[id]?.deleted==true) return json(mapOf("detail" to "deleted"),410)
     val text=payload["message"].asString
     val override=responses.poll()
     if(override==null || override.status.contains("200")) archive(id,requestId,text)
     val reply=transcript[id]?.firstOrNull { it.request_id==requestId && it.role=="assistant" }?.text ?: "Server reply"
     return override ?: json(mapOf("reply" to reply))
    }
    val id=path.removePrefix("/api/v1/conversations/").substringBefore('/')
    val item=metadata[id] ?: return json(mapOf("detail" to "missing"),404)
    if(item.deleted) return json(mapOf("detail" to "deleted"),410)
    if(path.contains("/requests/")) {
     if(disconnectStatus) { disconnectStatus=false; return MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AFTER_REQUEST) }
     val rid=path.substringAfterLast('/')
     val reply=transcript[id]?.firstOrNull { it.request_id==rid && it.role=="assistant" }?.text
     return json(ChatRequestStatus(rid,requestStates[rid] ?: if(reply!=null) "done" else "not_found",reply))
    }
    if(path.endsWith("/messages")) {
     val before=request.requestUrl!!.queryParameter("before")?.toLong()
     val limit=request.requestUrl!!.queryParameter("limit")?.toInt() ?: 50
     val records=transcript[id].orEmpty().filter { before==null || it.seq<before }
     val selected=records.takeLast(limit)
     val more=records.size>limit
     return json(MessagePage(selected,more,if(more) selected.first().seq else null))
    }
    if(request.method=="PATCH") { val renamed=item.copy(title=body(request)["title"].asString); metadata[id]=renamed; return json(renamed) }
    if(request.method=="DELETE") { metadata[id]=item.copy(deleted=true,preview="",message_count=0); transcript.remove(id); return MockResponse().setResponseCode(204) }
    return json(item)
   }
  }
  server.start(); dao=FakeDao(); repo=newRepository()
 }
 private fun json(value:Any,status:Int=200)=MockResponse().setResponseCode(status).setHeader("Content-Type","application/json").setBody(gson.toJson(value))
 private fun body(request:RecordedRequest)=JsonParser.parseString(request.body.clone().readUtf8()).asJsonObject
 private fun newRepository()=DefaultAtlasRepository(dao) { url,key -> ApiFactory.create(url,key,client) }
 private suspend fun connect()=repo.connect(server.url("/").toString(),token)
 private fun chatRequests()=requests.filter { it.path=="/api/v1/chat" }
 private fun archive(id:String,requestId:String,text:String) {
  val records=transcript.getOrPut(id) { mutableListOf() }
  if(records.any { it.request_id==requestId }) return
  records.add(TranscriptDto(++sequence,"$requestId-user",requestId,"user",text,sequence))
  records.add(TranscriptDto(++sequence,"$requestId-assistant",requestId,"assistant","Real reply to: $text",sequence))
  val item=metadata.getValue(id)
  metadata[id]=item.copy(message_count=records.size,preview=records.last().text,updated_at=sequence)
 }
 @After fun shutdown() { if(!stopped) server.shutdown(); client.connectionPool.evictAll(); client.dispatcher.executorService.shutdown() }

 @Test fun authenticatedHttpsChatUsesSelectedConversationAndCachesActualReply()=runBlocking {
  connect(); repo.send("Hello Atlas")
  assertTrue(requests.all { it.getHeader("Authorization")=="Bearer $token" })
  val payload=body(chatRequests().single())
  assertEquals("Hello Atlas",payload["message"].asString)
  assertEquals(repo.conversationId,payload["conversation_id"].asString)
  UUID.fromString(payload["request_id"].asString)
  assertTrue(payload["require_existing"].asBoolean)
  val rows=repo.messages().first()
  assertEquals(listOf("user","assistant"),rows.map { it.role })
  assertEquals("Real reply to: Hello Atlas",rows.last().text)
  assertEquals(DeliveryStatus.SENT,rows.first().delivery)
  assertEquals(2,repo.conversations().first().single().messageCount)
 }
 @Test fun droppedReplyRecoveryReusesRequestWithoutDuplicateBubbles()=runBlocking {
  connect(); responses.offer(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AFTER_REQUEST))
  try { repo.send("Remember this"); fail("Expected transport failure") } catch(_:java.io.IOException) {}
  val message=repo.messages().first().single()
  assertEquals(DeliveryStatus.RETRYABLE,message.delivery)
  repo.recover(message.id)
  val attempts=chatRequests().map { body(it)["request_id"].asString }
  assertEquals(1,attempts.size)
  assertTrue(requests.any { it.path?.contains("/requests/")==true })
  assertEquals(2,repo.messages().first().size)
  repo.refreshHistory(); assertEquals(2,repo.messages().first().size)
  repo.recover(message.id); assertEquals(1,chatRequests().size)
 }
 @Test fun explicitFailureRequiresConfirmedFreshRequest()=runBlocking {
  connect(); responses.offer(json(mapOf("detail" to "incomplete"),409))
  try { repo.send("Retry me"); fail("Expected conflict") } catch(_:retrofit2.HttpException) {}
  val row=repo.messages().first().single()
  assertEquals(DeliveryStatus.FAILED,row.delivery)
  try { repo.retry(row.id,false); fail("Confirmation required") } catch(_:IllegalArgumentException) {}
  repo.retry(row.id,true)
  assertNotEquals(body(chatRequests()[0])["request_id"].asString,body(chatRequests()[1])["request_id"].asString)
  assertEquals(1,repo.messages().first().count { it.role=="user" })
 }
 @Test fun pendingRequestIsRecoverableAfterReopenWithoutAutomaticPost()=runBlocking {
  connect()
  val id=UUID.randomUUID().toString()
  dao.insert(Message(id,repo.scope,"user","Pending",delivery=DeliveryStatus.PENDING,requestId=id,conversationId=repo.conversationId))
  repo=newRepository(); connect()
  assertTrue(chatRequests().isEmpty())
  assertEquals(DeliveryStatus.RETRYABLE,repo.messages().first().single().delivery)
  repo.recover(id)
  assertEquals(DeliveryStatus.UNCONFIRMED,repo.messages().first().single().delivery)
  assertTrue(chatRequests().isEmpty())
  repo.retry(id,false)
  assertEquals(id,body(chatRequests().single())["request_id"].asString)
 }
 @Test fun switchingChatsAndRestoringEmptyCacheKeepsContextsSeparate()=runBlocking {
  connect(); val first=repo.conversationId; repo.send("First chat")
  repo.newConversation("Second chat"); val second=repo.conversationId; repo.send("Second chat")
  repo.selectConversation(first); repo.refreshHistory()
  assertEquals("First chat",repo.messages().first().first().text)
  assertFalse(repo.messages().first().any { it.text.contains("Second chat") })
  repo.selectConversation(second)
  repo=newRepository(); connect(); assertEquals(second,repo.conversationId)
  val sent=chatRequests().size
  dao=FakeDao(); repo=newRepository(); connect(); repo.selectConversation(first); repo.refreshHistory()
  assertEquals(listOf("First chat","Real reply to: First chat"),repo.messages().first().map { it.text })
  assertEquals(sent,chatRequests().size)
 }
 @Test fun pagesRestoreFullHistoryBeyondPromptWindowWithoutDuplicates()=runBlocking {
  for(index in 0 until 53) archive("test-conversation",UUID.randomUUID().toString(),"Turn $index")
  connect(); repo.refreshHistory()
  assertEquals(50,repo.messages().first().size)
  assertTrue(repo.conversations().first().single().hasMore)
  repo.refreshHistory(true); repo.refreshHistory(true)
  assertEquals(106,repo.messages().first().size)
  assertFalse(repo.conversations().first().single().hasMore)
  repo.refreshHistory(); assertEquals(106,repo.messages().first().size)
 }
 @Test fun renameDeleteAndServerTombstonesUpdateCache()=runBlocking {
  connect(); repo.send("Keep in history"); val old=repo.conversationId
  repo.renameConversation(old,"Work projects")
  assertEquals("Work projects",repo.conversations().first().single().title)
  repo.newConversation("Other")
  repo.deleteConversation(old)
  assertFalse(repo.conversations().first().any { it.id==old })
  val current=repo.conversationId
  metadata[current]=metadata.getValue(current).copy(deleted=true,preview="",message_count=0)
  repo.refreshConversations()
  assertTrue(repo.conversations().first().isEmpty())
  assertEquals("",repo.conversationId)
 }
 @Test fun missingServerHistoryPreservesReadOnlyCache()=runBlocking {
  connect(); repo.send("Only remaining copy")
  metadata.clear(); transcript.clear()
  repo.refreshConversations()
  assertFalse(repo.conversations().first().single().serverAvailable)
  assertEquals(2,repo.messages().first().size)
  val before=chatRequests().size
  try { repo.send("Must not recreate missing chat"); fail("Should be read only") } catch(_:IllegalArgumentException) {}
  assertEquals(before,chatRequests().size)
 }
 @Test fun offlineRestartOpensCacheWithoutPretendingToBeDemo()=runBlocking {
  connect(); repo.send("Available offline")
  val url=server.url("/").toString()
  server.shutdown(); stopped=true
  repo=newRepository(); repo.connect(url,token)
  assertTrue(repo.offline); assertFalse(repo.demo)
  assertEquals(2,repo.messages().first().size)
 }
 @Test fun demoAndCredentialsRemainIsolatedAndInvalidInputNeverPosts()=runBlocking {
  repo.useDemo(); repo.seed(); repo.send("Demo only")
  val demoId=repo.conversationId
  connect(); assertTrue(repo.messages().first().isEmpty()); repo.send("Live only")
  val scope=repo.scope; healthStatus=401
  try { repo.connect(server.url("/").toString(),"other-token"); fail("Unauthorized") } catch(_:retrofit2.HttpException) {}
  assertEquals(scope,repo.scope)
  val before=chatRequests().size
  for(text in listOf(" ","x".repeat(8001))) { try { repo.send(text); fail("Invalid input") } catch(_:IllegalArgumentException) {} }
  assertEquals(before,chatRequests().size)
  repo.useDemo(); repo.seed(); assertEquals(demoId,repo.conversationId)
  assertEquals("Demo only",repo.messages().first().first().text)
 }
 @Test fun checkingPendingAndInterruptedRequestsNeverStartsAnotherInference()=runBlocking {
  connect()
  val id=UUID.randomUUID().toString()
  dao.insert(Message(id,repo.scope,"user","Pending on server",delivery=DeliveryStatus.RETRYABLE,requestId=id,conversationId=repo.conversationId))
  requestStates[id]="pending"
  repo.recover(id)
  assertEquals(DeliveryStatus.RETRYABLE,repo.messages().first().single().delivery)
  assertTrue(repo.messages().first().single().deliveryError!!.contains("still processing"))
  requestStates[id]="interrupted"
  repo.recover(id)
  assertEquals(DeliveryStatus.FAILED,repo.messages().first().single().delivery)
  assertTrue(chatRequests().isEmpty())
 }
 @Test fun statusTransportFailureKeepsRecoveryStateAndOriginalRequest()=runBlocking {
  connect()
  val id=UUID.randomUUID().toString()
  dao.insert(Message(id,repo.scope,"user","Uncertain",delivery=DeliveryStatus.RETRYABLE,requestId=id,conversationId=repo.conversationId))
  disconnectStatus=true
  try { repo.recover(id); fail("Expected disconnected status check") } catch(_:java.io.IOException) {}
  val row=repo.messages().first().single()
  assertEquals(DeliveryStatus.RETRYABLE,row.delivery)
  assertEquals(id,row.requestId)
  assertTrue(chatRequests().isEmpty())
 }
 @Test fun rateLimitGuidanceHonorsRetryAfterWithoutAutomaticResend()=runBlocking {
  connect()
  responses.offer(json(mapOf("detail" to "rate limit"),429).setHeader("Retry-After","45"))
  try { repo.send("Wait for quota"); fail("Expected rate limit") } catch(_:retrofit2.HttpException) {}
  val row=repo.messages().first().single()
  assertEquals(DeliveryStatus.FAILED,row.delivery)
  assertTrue(row.deliveryError!!.contains("45 seconds"))
  assertEquals(1,chatRequests().size)
 }

}
