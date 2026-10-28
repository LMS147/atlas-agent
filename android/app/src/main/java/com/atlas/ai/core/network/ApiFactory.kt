package com.atlas.ai.core.network

import okhttp3.OkHttpClient
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

import com.atlas.ai.data.remote.AtlasApi

object ApiFactory {
 fun normalize(raw: String): String {
  val url = requireNotNull(raw.trim().toHttpUrlOrNull()) { "Enter a valid HTTPS server URL" }
  require(url.isHttps && url.username.isEmpty() && url.password.isEmpty() && url.query == null && url.fragment == null) {
   "Use HTTPS without embedded credentials, a query, or fragment"
  }
  return url.toString().trimEnd('/') + "/"
 }
 fun create(url: String, token: String): AtlasApi {
  require(token.isNotBlank() && token.none { it == '\r' || it == '\n' }) { "Enter a valid Atlas access token" }
  val client = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(90, TimeUnit.SECONDS)
   .callTimeout(100, TimeUnit.SECONDS).followRedirects(false).followSslRedirects(false)
   .retryOnConnectionFailure(false).addInterceptor { chain ->
    chain.proceed(chain.request().newBuilder().header("Authorization", "Bearer $token").build())
   }.build()
  return Retrofit.Builder().baseUrl(normalize(url)).client(client).addConverterFactory(GsonConverterFactory.create()).build().create(AtlasApi::class.java)
 }
}
