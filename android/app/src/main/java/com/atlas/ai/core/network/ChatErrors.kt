package com.atlas.ai.core.network

import java.io.IOException
import retrofit2.HttpException

object ChatErrors {
 fun message(error: Exception): String = when (error) {
  is HttpException -> when (error.code()) {
   401, 403 -> "Access token rejected. Check your Atlas credentials in Server setup."
   404 -> "Atlas API route was not found. Check the HTTPS server URL and backend version."
   409 -> "Atlas cannot safely replay this request. Check your conversation and memory before sending again."
   422 -> "Atlas rejected the message format. Check the backend version and message length."
   429 -> "Groq is rate limited. Wait before choosing Send again."
   502 -> "The AI provider is unavailable. Check the server's Groq key, model, and connection."
   504 -> "The AI provider timed out. Check your memory before choosing Send again."
   else -> "Atlas returned HTTP ${error.code()}. The request may not have completed."
  }
  is IOException -> "Connection interrupted. Check your internet and tunnel, then check for the reply."
  is MessageNotSavedException -> "The message could not be saved on this device. Your draft has been restored."
  is IllegalArgumentException -> error.message ?: "Check the message and server settings."
  is InvalidReplyException -> "Atlas returned an invalid reply. Check for the reply before sending anything again."
  else -> "Atlas could not complete this operation. Check your connection and server."
 }
}
class MessageNotSavedException(cause: Exception) : Exception(cause)
class InvalidReplyException : Exception()
