package com.atlas.ai.feature.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.atlas.ai.data.local.Message
import com.atlas.ai.domain.model.DeliveryStatus
import com.atlas.ai.domain.model.UiState
import com.atlas.ai.navigation.AtlasViewModel
import com.atlas.ai.ui.theme.*
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable internal fun Chat(s: UiState, vm: AtlasViewModel) {
 var draft by rememberSaveable(s.activeConversation?.id) { mutableStateOf("") }
 var confirmResend by rememberSaveable(s.activeConversation?.id) { mutableStateOf<String?>(null) }
 val list = rememberLazyListState()
 val waiting = s.messages.any { it.role == "user" && it.delivery == DeliveryStatus.PENDING }
 val unresolved = s.messages.any { it.role == "user" && it.delivery == DeliveryStatus.RETRYABLE }
 LaunchedEffect(s.restoredDraft) {
  s.restoredDraft?.let { draft = it; vm.consumeRestoredDraft() }
 }
 LaunchedEffect(s.messages.lastOrNull()?.id, waiting) {
  if (s.messages.isNotEmpty()) list.animateScrollToItem(if(waiting) s.messages.size else s.messages.size - 1)
 }
 Column(Modifier.fillMaxSize().imePadding()) {
  Row(Modifier.fillMaxWidth().padding(horizontal=16.dp),verticalAlignment=Alignment.CenterVertically) {
   Text(s.activeConversation?.title ?: "Choose a conversation",modifier=Modifier.weight(1f),maxLines=1,overflow=TextOverflow.Ellipsis,fontWeight=FontWeight.SemiBold)
   TextButton(enabled=!s.busy,onClick={ vm.navigate("Conversations") }) { Text("History") }
   TextButton(enabled=!s.busy,onClick=vm::newConversation) { Text("New") }
  }
  Column(Modifier.fillMaxWidth().background(Panel).padding(horizontal = 20.dp, vertical = 10.dp)) {
   Text(if(s.demo) "Demo conversation" else s.connectionStatus, color = Cyan, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
   Text(if(s.demo) "Local sample replies · no AI requests" else s.serverUrl, color = Muted, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
  }
  LazyColumn(state = list, modifier = Modifier.weight(1f).fillMaxWidth(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
   if(s.activeConversation?.hasMore == true) item(key="earlier") {
    TextButton(enabled=!s.busy,onClick=vm::loadEarlier) { Text("Load earlier messages") }
   }
   if(s.activeConversation?.serverAvailable == false) item(key="cache-only") {
    Text("Cached conversation · history is unavailable on this server. Start a new chat to send messages.",color=Cyan)
   }
   if(!s.demo && s.activeConversation != null) item(key="refresh") {
    TextButton(enabled=!s.busy,onClick=vm::refreshChat) { Text("Refresh saved history") }
   }
   if(s.messages.isEmpty()) item {
    Column(verticalArrangement = Arrangement.spacedBy(24.dp)) {
     AtlasMark(); Heading("Hello. I’m Atlas.", "What are we working on today?")
     AtlasCard {
      Text(if(s.demo) "Explore demo mode" else "Your Atlas is ready", fontWeight = FontWeight.SemiBold)
      Text(if(s.demo) "Sample replies are labelled and saved locally. Connect your server for real AI chat." else "Send a message to your server. Atlas uses Groq and your saved memory to reply.", color = Muted)
     }
     Text("QUICK ACTIONS", color = Muted, fontSize = 11.sp, letterSpacing = 2.sp)
     listOf("Memory" to "Agent profile", "Files" to "Server status").forEach { pair ->
      Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
       listOf(pair.first, pair.second).forEach { page ->
        OutlinedButton(enabled = !s.busy, modifier = Modifier.weight(1f).height(62.dp), shape = RoundedCornerShape(16.dp), onClick = { vm.navigate(page) }) { Text(page) }
       }
      }
     }
    }
   }
   items(s.messages, key = { it.id }) { msg ->
    MessageBubble(msg, s.demo, s.timestamps, s.busy,
     onRecover = { vm.retry(msg.id) }, onResend = { confirmResend = msg.id })
   }
   if(waiting) item(key = "waiting") {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
     CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
     Text(if(s.demo) "Preparing demo reply…" else "Waiting for Atlas…", color = Muted, fontSize = 13.sp)
    }
   }
  }
  if(unresolved) Text("Check for the missing reply above before sending another message.", color = Cyan, fontSize = 12.sp, modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp))
  Row(Modifier.fillMaxWidth().background(Panel).padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
   OutlinedTextField(
    value = draft, onValueChange = { draft = it }, placeholder = { Text("Ask me anything…") },
    modifier = Modifier.weight(1f), maxLines = 5, shape = RoundedCornerShape(24.dp), enabled = !s.busy,
    isError = draft.trim().length > 8000,
    supportingText = { if(draft.length > 7500) Text("${draft.trim().length}/8,000 characters") }
   )
   FilledIconButton(enabled = !s.busy && s.activeConversation != null && s.activeConversation.serverAvailable && !unresolved && draft.isNotBlank() && draft.trim().length <= 8000,
    onClick = { if(vm.send(draft)) draft = "" }) { Icon(Icons.AutoMirrored.Filled.Send, "Send message") }
  }
 }
 confirmResend?.let { id ->
  AlertDialog(onDismissRequest = { confirmResend = null }, title = { Text("Send this message again?") },
   text = { Text("This creates a new request. Atlas may have saved a memory before the earlier request failed. Check the conversation and memory first.") },
   confirmButton = { TextButton(enabled = !s.busy, onClick = { confirmResend = null; vm.retry(id, newRequest = true) }) { Text("Send again") } },
   dismissButton = { TextButton(onClick = { confirmResend = null }) { Text("Cancel") } })
 }
}

@Composable private fun MessageBubble(msg: Message, demo: Boolean, timestamps: Boolean, busy: Boolean, onRecover: () -> Unit, onResend: () -> Unit) {
 val user = msg.role == "user"
 Column(Modifier.fillMaxWidth(), horizontalAlignment = if(user) Alignment.End else Alignment.Start) {
  Surface(color = if(user) Color(0xFF225AA8) else Panel, shape = RoundedCornerShape(18.dp), modifier = Modifier.widthIn(max = 320.dp)) {
   Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
    Text(if(user) "YOU" else if(demo) "ATLAS · DEMO" else "ATLAS", fontSize = 10.sp, color = Cyan, fontWeight = FontWeight.Bold)
    Text(msg.text, lineHeight = 23.sp)
   }
  }
  if(user) {
   Text(when(msg.delivery) {
    DeliveryStatus.PENDING -> "Sending…"
    DeliveryStatus.RETRYABLE -> "Reply not received"
    DeliveryStatus.FAILED -> "Request failed"
    else -> "Sent"
   }, color = if(msg.delivery in listOf(DeliveryStatus.RETRYABLE, DeliveryStatus.FAILED)) Cyan else Muted, fontSize = 11.sp, modifier = Modifier.padding(top = 5.dp))
   msg.deliveryError?.let { Text(it, color = Muted, fontSize = 12.sp, modifier = Modifier.widthIn(max = 320.dp)) }
   if(msg.delivery == DeliveryStatus.RETRYABLE) TextButton(enabled = !busy, onClick = onRecover) { Text("Check for reply") }
   if(msg.delivery == DeliveryStatus.FAILED) TextButton(enabled = !busy, onClick = onResend) { Text("Send again…") }
  }
  if(timestamps) Text(SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(msg.createdAt)), color = Muted, fontSize = 10.sp, modifier = Modifier.padding(6.dp))
 }
}
