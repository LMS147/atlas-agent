package com.atlas.ai.feature.chat

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.atlas.ai.navigation.AtlasViewModel
import com.atlas.ai.domain.model.UiState
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlinx.coroutines.launch

import com.atlas.ai.ui.theme.*

@Composable internal fun Chat(s: UiState, vm: AtlasViewModel) {
 var draft by rememberSaveable { mutableStateOf("") }
 val list = rememberLazyListState()
 LaunchedEffect(s.messages.size) { if(s.messages.isNotEmpty()) list.animateScrollToItem(s.messages.size - 1) }
 Column(Modifier.fillMaxSize().imePadding()) {
  LazyColumn(state = list, modifier = Modifier.weight(1f).fillMaxWidth(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
   if(s.messages.isEmpty()) item {
    Column(verticalArrangement = Arrangement.spacedBy(24.dp)) {
     AtlasMark(); Heading("Hello. I’m Atlas.", "A little clarity for whatever comes next.")
     AtlasCard { Text("What are we working on today?", fontWeight = FontWeight.SemiBold); Text(if(s.demo) "Explore the app with sample data. Demo replies are clearly labelled and saved locally." else "Your messages go to your own Atlas server.", color = Muted) }
     Text("QUICK ACTIONS", color = Muted, fontSize = 11.sp, letterSpacing = 2.sp)
     listOf("Memory" to "Agent profile", "Files" to "Server status").forEach { pair -> Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) { listOf(pair.first,pair.second).forEach { page -> OutlinedButton(enabled = !s.busy, modifier = Modifier.weight(1f).height(62.dp), shape = RoundedCornerShape(16.dp), onClick = { vm.navigate(page) }) { Text(page) } } } }
    }
   }
   items(s.messages, key = { it.id }) { msg ->
    Column(Modifier.fillMaxWidth(), horizontalAlignment = if(msg.role == "user") Alignment.End else Alignment.Start) {
     Surface(color = if(msg.role == "user") Color(0xFF225AA8) else Panel, shape = RoundedCornerShape(18.dp), modifier = Modifier.widthIn(max = 320.dp)) { Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) { Text(if(msg.role == "user") "YOU" else if(s.demo) "ATLAS · DEMO" else "ATLAS", fontSize = 10.sp, color = Cyan, fontWeight = FontWeight.Bold); Text(msg.text, lineHeight = 23.sp) } }
     if(s.timestamps) Text(SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(msg.createdAt)), color = Muted, fontSize = 10.sp, modifier = Modifier.padding(6.dp))
    }
   }
  }
  Row(Modifier.fillMaxWidth().background(Panel).padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
   OutlinedTextField(value = draft, onValueChange = { draft = it }, placeholder = { Text("Ask me anything…") }, modifier = Modifier.weight(1f), maxLines = 5, shape = RoundedCornerShape(24.dp), enabled = !s.busy)
   FilledIconButton(enabled = !s.busy && draft.isNotBlank(), onClick = { vm.send(draft); draft = "" }) { Icon(Icons.AutoMirrored.Filled.Send, "Send message") }
  }
 }
}
