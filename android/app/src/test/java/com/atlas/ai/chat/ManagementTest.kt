package com.atlas.ai.chat

import com.atlas.ai.core.network.ApiFactory
import com.atlas.ai.core.network.BoundedFiles
import com.atlas.ai.data.repository.DefaultAtlasRepository
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.tls.HandshakeCertificates
import okhttp3.tls.HeldCertificate
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import retrofit2.HttpException

class ManagementTest {
 private lateinit var server: MockWebServer
 private lateinit var repo: DefaultAtlasRepository
 private val token="management-token-"+"x".repeat(32)
 private fun json(body: String, status: Int = 200)=MockResponse().setResponseCode(status).setHeader("Content-Type","application/json").setBody(body)
 @Before fun setup() {
  val cert=HeldCertificate.Builder().addSubjectAlternativeName("localhost").build()
  val trust=HandshakeCertificates.Builder().addTrustedCertificate(cert.certificate).build()
  val serverCerts=HandshakeCertificates.Builder().heldCertificate(cert).build()
  val client=OkHttpClient.Builder().sslSocketFactory(trust.sslSocketFactory(),trust.trustManager).protocols(listOf(Protocol.HTTP_1_1)).build()
  server=MockWebServer();server.useHttps(serverCerts.sslSocketFactory(),false);server.start()
  repo=DefaultAtlasRepository(FakeDao()) { url,key -> ApiFactory.create(url,key,client) }
  server.enqueue(json("""{"status":"ok"}"""))
  server.enqueue(json("""[{"id":"chat-test","title":"Test","created_at":1,"updated_at":1,"message_count":0,"preview":"","deleted":false}]"""))
  runBlocking { repo.connect(server.url("/").toString(),token) }
  server.takeRequest();server.takeRequest()
 }
 @After fun close() {server.shutdown()}

 @Test fun uploadsAndDownloadsPreserveBinaryAndAuthenticate()=runBlocking {
  val bytes=byteArrayOf(0,1,2,-1)
  server.enqueue(json("""{"name":"test.bin","path":"workspace/test.bin","directory":false,"size_bytes":4,"writable":true}""",201))
  repo.upload("test.bin",bytes)
  val sent=server.takeRequest()
  assertEquals("Bearer $token",sent.getHeader("Authorization"))
  assertEquals("test.bin",sent.requestUrl!!.queryParameter("name"))
  assertArrayEquals(bytes,sent.body.readByteArray())
  server.enqueue(MockResponse().setBody(okio.Buffer().write(bytes)))
  assertArrayEquals(bytes,repo.download("workspace/test.bin"))
  assertEquals("workspace/test.bin",server.takeRequest().requestUrl!!.queryParameter("path"))
 }
 @Test fun staleFileSavePropagatesConflictAndKeepsOriginalRevision()=runBlocking {
  val revision="a".repeat(64)
  server.enqueue(json("""{"path":"workspace/a.txt","content":"old","revision":"$revision","writable":true}"""))
  val doc=repo.document("workspace/a.txt")
  server.takeRequest()
  server.enqueue(json("""{"detail":"changed"}""",409))
  try {repo.editFile(doc.path,"new",doc.revision);fail("Conflict must not appear successful")}
  catch(error:HttpException){assertEquals(409,error.code())}
  val request=server.takeRequest()
  assertTrue(request.body.readUtf8().contains(revision))
  assertEquals("old",doc.content)
 }
 @Test fun memoryMutationsRefreshCacheAndCompactionUsesPreviewRevision()=runBlocking {
  server.enqueue(MockResponse().setResponseCode(204))
  server.enqueue(json("""[{"id":"updated","section":"People","fact":"New fact"}]"""))
  repo.editMemory("old","People","New fact")
  assertEquals("PATCH",server.takeRequest().method);server.takeRequest()
  assertEquals("New fact",repo.memories().first().single().fact)
  server.enqueue(MockResponse().setResponseCode(204));server.enqueue(json("[]"))
  repo.deleteMemory("updated")
  assertEquals("DELETE",server.takeRequest().method);server.takeRequest()
  assertTrue(repo.memories().first().isEmpty())
  val plan="""{"revision":"${"b".repeat(64)}","before_chars":30,"after_chars":20,"removed_entries":1}"""
  server.enqueue(json(plan));val preview=repo.compactPlan();assertEquals("GET",server.takeRequest().method)
  server.enqueue(json(plan));server.enqueue(json("[]"));repo.compact(preview.revision)
  assertTrue(server.takeRequest().body.readUtf8().contains(preview.revision));server.takeRequest()
 }
 @Test fun monitoringKeepsUnavailableMetricsNull()=runBlocking {
  server.enqueue(json("""{"sampled_at":123,"device_cpu_percent":null,"process_cpu_percent":1.5,"ram":null,"process_rss_bytes":null,"storage":{"total_bytes":1000,"used_bytes":400,"free_bytes":600},"device_uptime_seconds":null,"service":{"pid":42,"uptime_seconds":12,"threads":3,"requests":8,"errors":1,"active_requests":1},"unavailable":["device CPU","device RAM"]}"""))
  val metrics=repo.monitoring()
  assertNull(metrics.device_cpu_percent);assertNull(metrics.ram);assertEquals(42,metrics.service.pid)
  assertEquals(600L,metrics.storage!!.free_bytes)
 }
 @Test fun boundedReaderRejectsOversizedInputWithoutTruncation() {
  assertArrayEquals(byteArrayOf(1,2),BoundedFiles.read(byteArrayOf(1,2).inputStream(),2))
  try {BoundedFiles.read(byteArrayOf(1,2,3).inputStream(),2);fail("Oversized file accepted")}
  catch(_:IllegalArgumentException){}
 }
}
