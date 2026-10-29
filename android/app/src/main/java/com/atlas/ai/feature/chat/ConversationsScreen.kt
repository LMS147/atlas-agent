package com.atlas.ai.feature.chat

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.atlas.ai.data.local.Conversation
import com.atlas.ai.domain.model.UiState
import com.atlas.ai.navigation.AtlasViewModel
import com.atlas.ai.ui.theme.*
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun ConversationsScreen(s: UiState, vm: AtlasViewModel) {
 var query by rememberSaveable { mutableStateOf("") }
 var editing by remember { mutableStateOf<Conversation?>(null) }
 var deleting by remember { mutableStateOf<Conversation?>(null) }
 var title by rememberSaveable { mutableStateOf("") }
 val rows = s.conversations.filter { it.title.contains(query,true) || it.preview.contains(query,true) }
 Column(Modifier.fillMaxSize().padding(horizontal=20.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
  Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceBetween) {
   Text(if(s.demo) "Saved on this device" else "Your saved chats",color=Muted)
   Button(enabled=!s.busy,onClick=vm::newConversation) { Text("New chat") }
  }
  OutlinedTextField(query,{ query=it },label={ Text("Search titles and previews") },singleLine=true,modifier=Modifier.fillMaxWidth())
  LazyColumn(verticalArrangement=Arrangement.spacedBy(12.dp),contentPadding=PaddingValues(bottom=20.dp)) {
   if(rows.isEmpty()) item { Text(if(query.isBlank()) "No saved conversations. Start a new chat." else "No matching conversations.",color=Muted) }
   items(rows,key={ it.id }) { row ->
    OutlinedCard(onClick={ vm.openConversation(row.id) },enabled=!s.busy,modifier=Modifier.fillMaxWidth(),colors=CardDefaults.outlinedCardColors(containerColor=Panel)) {
     Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
      Text(row.title,fontWeight=FontWeight.SemiBold,maxLines=2,overflow=TextOverflow.Ellipsis)
      Text(row.preview.ifBlank { "No messages yet" },color=Muted,maxLines=2,overflow=TextOverflow.Ellipsis)
      Text("${row.messageCount} saved messages · ${SimpleDateFormat("dd MMM · HH:mm",Locale.getDefault()).format(Date(row.updatedAt))}",color=Muted,fontSize=11.sp)
      if(!row.serverAvailable && !s.demo) Text("Cached only · unavailable on the server",color=Cyan,fontSize=11.sp)
      Row {
       TextButton(enabled=!s.busy && (s.demo || row.serverAvailable),onClick={ editing=row; title=row.title }) { Text("Rename") }
       TextButton(enabled=!s.busy,onClick={ deleting=row }) { Text(if(row.serverAvailable || s.demo) "Delete" else "Delete cache") }
      }
     }
    }
   }
  }
 }
 editing?.let { row ->
  AlertDialog(onDismissRequest={ editing=null },title={ Text("Rename conversation") },
   text={ OutlinedTextField(title,{ title=it },label={ Text("Title") },supportingText={ Text("${title.trim().length}/80") },isError=title.trim().length>80) },
   confirmButton={ TextButton(enabled=!s.busy && title.isNotBlank() && title.trim().length<=80,onClick={ editing=null; vm.renameConversation(row.id,title) }) { Text("Save") } },
   dismissButton={ TextButton(onClick={ editing=null }) { Text("Cancel") } })
 }
 deleting?.let { row ->
  AlertDialog(onDismissRequest={ deleting=null },title={ Text("Delete this conversation?") },
   text={ Text(if(s.demo || !row.serverAvailable) "This removes the cached conversation and its messages from this device. Saved memories stay intact." else "This removes the conversation, messages, and context from your server and this device. Other devices update when they sync. Saved memories stay intact.") },
   confirmButton={ TextButton(enabled=!s.busy,onClick={ deleting=null; vm.deleteConversation(row.id) }) { Text("Delete") } },
   dismissButton={ TextButton(onClick={ deleting=null }) { Text("Cancel") } })
 }
}
