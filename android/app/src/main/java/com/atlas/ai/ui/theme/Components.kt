package com.atlas.ai.ui.theme

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

internal val Navy = Color(0xFF08131F)
internal val Panel = Color(0xFF142638)
internal val Blue = Color(0xFF539FFF)
internal val Cyan = Color(0xFF70D6F5)
internal val Muted = Color(0xFFA6B9CD)
internal val pages = listOf("Chat", "Conversations", "Memory", "Agent profile", "Files", "Tools", "Server status", "Settings")
internal val pageIcons = listOf(Icons.Default.ChatBubbleOutline, Icons.Default.History, Icons.Default.Psychology, Icons.Default.PersonOutline, Icons.Default.FolderOpen, Icons.Default.Build, Icons.Default.Dns, Icons.Default.Settings)

@Composable fun AtlasMark(modifier: Modifier = Modifier) {
 Canvas(modifier.size(72.dp)) {
  val p = Path().apply { moveTo(size.width*.5f, size.height*.08f); lineTo(size.width*.08f,size.height*.87f); quadraticTo(0f,size.height, size.width*.25f,size.height*.91f); lineTo(size.width*.5f,size.height*.46f); lineTo(size.width*.75f,size.height*.91f); quadraticTo(size.width,size.height,size.width*.92f,size.height*.87f); close() }
  drawPath(p, Brush.linearGradient(listOf(Cyan, Blue, Color(0xFF7967FF)), Offset.Zero, Offset(size.width,size.height)))
 }
}
@Composable internal fun Heading(title: String, subtitle: String) {
 Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
 Spacer(Modifier.height(8.dp)); Text(subtitle, color = Muted, style = MaterialTheme.typography.bodyMedium)
}
@Composable internal fun AtlasCard(content: @Composable ColumnScope.() -> Unit) {
 Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) {
  Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp), content = content)
 }
}
