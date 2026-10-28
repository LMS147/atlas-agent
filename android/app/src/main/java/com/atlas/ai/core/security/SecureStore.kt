package com.atlas.ai.core.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Only ciphertext is persisted. Groq keys belong on the server, never in this app. */
class SecureStore(context: Context) {
 private val prefs = context.getSharedPreferences("atlas_connection", Context.MODE_PRIVATE)
 private fun key(): SecretKey {
  val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
  (store.getKey("atlas_connection_v1", null) as? SecretKey)?.let { return it }
  return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
   init(KeyGenParameterSpec.Builder("atlas_connection_v1", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
    .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
  }.generateKey()
 }
 fun save(url: String, token: String) {
  val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
  val payload = "$url\n$token".toByteArray(Charsets.UTF_8)
  val encrypted = cipher.doFinal(payload)
  check(prefs.edit().putString("iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
   .putString("value", Base64.encodeToString(encrypted, Base64.NO_WRAP)).commit()) { "Could not save connection" }
 }
 fun load(): Pair<String, String>? {
  val value = prefs.getString("value", null) ?: return null
  val iv = prefs.getString("iv", null) ?: error("Saved connection is incomplete")
  val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply {
   init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
  }
  val parts = String(cipher.doFinal(Base64.decode(value, Base64.NO_WRAP)), Charsets.UTF_8).split('\n', limit = 2)
  require(parts.size == 2)
  return parts[0] to parts[1]
 }
 fun clear() { check(prefs.edit().clear().commit()) }
}
