package com.atlas.ai.navigation

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
import com.atlas.ai.feature.dashboard.*
import com.atlas.ai.feature.chat.*
import com.atlas.ai.feature.memory.*
import com.atlas.ai.feature.files.*
import com.atlas.ai.feature.automation.*
import com.atlas.ai.feature.monitoring.*
import com.atlas.ai.feature.settings.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun AtlasApp(vm: AtlasViewModel) {
 val s by vm.state.collectAsStateWithLifecycle()
 val drawer = rememberDrawerState(DrawerValue.Closed)
 val scope = rememberCoroutineScope()
 MaterialTheme(colorScheme = darkColorScheme(primary = Blue, secondary = Cyan, background = Navy, surface = Navy, surfaceVariant = Panel, onBackground = Color.White, onSurface = Color.White)) {
  val onboarding = s.screen in listOf("Welcome", "Server setup")
  BackHandler(enabled = drawer.isOpen || s.screen != "Welcome" && s.screen != "Chat") {
   if (drawer.isOpen) scope.launch { drawer.close() } else vm.navigate(if(onboarding) "Welcome" else "Chat")
  }
  ModalNavigationDrawer(drawerState = drawer, gesturesEnabled = !onboarding && !s.busy, drawerContent = {
   ModalDrawerSheet(drawerContainerColor = Navy) {
    Column(Modifier.padding(24.dp)) { AtlasMark(); Text("Atlas", fontSize = 28.sp, fontWeight = FontWeight.Bold); Text(if(s.demo) "Demo workspace" else "Your server workspace", color = Cyan) }
    pages.forEachIndexed { i, page -> NavigationDrawerItem(label = { Text(page) }, selected = s.screen == page, icon = { Icon(pageIcons[i], null) }, onClick = { if (!s.busy) { vm.navigate(page); scope.launch { drawer.close() } } }, modifier = Modifier.padding(horizontal = 12.dp)) }
   }
  }) {
   Scaffold(containerColor = Navy, topBar = {
    if (!onboarding) TopAppBar(title = { Column { Text(if(s.screen == "Chat") "Atlas" else s.screen, fontWeight = FontWeight.Bold); Text(if(s.demo) "DEMO MODE · LOCAL PREVIEW" else s.connectionStatus.uppercase(), color = Cyan, fontSize = 10.sp, letterSpacing = 1.sp) } }, navigationIcon = {
     IconButton(enabled = !s.busy, onClick = { scope.launch { drawer.open() } }) { Icon(Icons.Default.Menu, "Open navigation") }
    }, actions = { if(s.screen == "Server status" || s.screen == "Memory" || s.screen == "Conversations") IconButton(enabled = !s.busy, onClick = { vm.navigate(s.screen) }) { Icon(Icons.Default.Refresh, "Refresh") } })
   }) { padding ->
    Column(Modifier.fillMaxSize().padding(padding)) {
     if(s.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
     s.error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.fillMaxWidth().background(Panel).padding(16.dp)) }
     s.notice?.let { Text(it, color = Cyan, modifier = Modifier.padding(16.dp)) }
     when(s.screen) {
      "Welcome" -> Welcome(vm, s.busy)
      "Server setup" -> Setup(vm, s.busy)
      "Chat" -> Chat(s, vm)
      "Conversations" -> com.atlas.ai.feature.chat.ConversationsScreen(s, vm)
      "Memory" -> Memories(s, vm)
      "Agent profile" -> ProfileScreen(s, vm)
      "Files" -> FilesScreen(s, vm)
      "Tools" -> ToolsScreen(s, vm)
      "Server status" -> MonitoringScreen(s, vm)
      "Settings" -> Settings(s, vm)
     }
    }
   }
  }
 }
}
