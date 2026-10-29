package com.atlas.ai.feature.memory

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

@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun Memories(s: UiState, vm: AtlasViewModel) {
 var search by rememberSaveable { mutableStateOf("") }; var filter by rememberSaveable { mutableStateOf("All") }; var add by rememberSaveable { mutableStateOf(false) }; var fact by rememberSaveable { mutableStateOf("") }; var section by rememberSaveable { mutableStateOf("Projects") }
 var editId by rememberSaveable { mutableStateOf<String?>(null) }
 var deleteId by rememberSaveable { mutableStateOf<String?>(null) }
 LaunchedEffect(s.notice) { if(s.notice == "Memory updated.") { add=false; editId=null; fact="" } }
 val sections = listOf("Projects", "User Preferences", "Decisions", "People")
 Column(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
  OutlinedTextField(search, { search = it }, placeholder = { Text("Search memory…") }, leadingIcon = { Icon(Icons.Default.Search, null) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
  ScrollableTabRow(selectedTabIndex = (listOf("All") + sections).indexOf(filter), edgePadding = 0.dp, containerColor = Navy) { (listOf("All") + sections).forEach { category -> Tab(selected = filter == category, onClick = { filter = category }, text = { Text(category) }) } }
  Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { Text(if(s.demo) "Sample memories" else "Saved memories", color = Muted); TextButton(enabled = !s.busy, onClick = { editId=null; fact=""; add = true }) { Icon(Icons.Default.Add, null); Text("Remember") } }
  TextButton(enabled=!s.demo && !s.busy,onClick={vm.previewCompact()}) { Text("Preview compaction") }
  val rows = s.memories.filter { (filter == "All" || it.section == filter) && (it.fact.contains(search,true) || it.section.contains(search,true)) }
  LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp), contentPadding = PaddingValues(bottom = 20.dp)) { items(rows, key = { it.id }) { memory -> AtlasCard { Text(memory.section.uppercase(), color = Cyan, fontSize = 10.sp, letterSpacing = 1.sp); Text(memory.fact, lineHeight = 23.sp)
   Row { TextButton(enabled=!s.demo && !s.busy,onClick={editId=memory.id;fact=memory.fact;section=memory.section;add=true}){Text("Edit")}; TextButton(enabled=!s.demo && !s.busy,onClick={deleteId=memory.id}){Text("Delete")} } } }; if(rows.isEmpty()) item { Text("No memories match your search.", color = Muted) } }
 }
 if(add) AlertDialog(onDismissRequest = { add = false }, title = { Text(if(editId == null) "Remember a fact" else "Edit memory") }, text = { Column(verticalArrangement = Arrangement.spacedBy(12.dp)) { s.error?.let { Text(it,color=MaterialTheme.colorScheme.error) }; Text("Section", color = Muted); sections.forEach { name -> Row(verticalAlignment = Alignment.CenterVertically) { RadioButton(selected = section == name, onClick = { section = name }); Text(name) } }; OutlinedTextField(fact, { fact = it.take(300) }, label = { Text("Fact (${fact.length}/300)") }) } }, confirmButton = { TextButton(enabled = fact.isNotBlank() && !s.busy, onClick = { if(editId == null) { vm.remember(section,fact); fact="";add=false } else vm.editMemory(editId!!,section,fact) }) { Text("Save") } }, dismissButton = { TextButton(onClick = { add = false }) { Text("Cancel") } })

 deleteId?.let { id -> AlertDialog(onDismissRequest={deleteId=null},title={Text("Delete memory?")},text={Text("This removes the saved fact used in future replies. Existing chat messages keep their original text.")},confirmButton={TextButton(enabled=!s.busy,onClick={vm.deleteMemory(id);deleteId=null}){Text("Delete")}},dismissButton={TextButton(onClick={deleteId=null}){Text("Cancel")}}) }
 s.compactPlan?.let { plan -> AlertDialog(onDismissRequest={vm.dismissCompact()},title={Text("Compact memory?")},text={Column {
  Text("${plan.before_chars} → ${plan.after_chars} characters. ${plan.removed_entries} duplicate entries removed.")
  Text("Only exact duplicates and repeated blank lines are removed. Unique facts and other Markdown are preserved. A backup is saved before changes.")
  s.error?.let { Text(it,color=MaterialTheme.colorScheme.error) }
 }},confirmButton={TextButton(enabled=!s.busy,onClick={vm.compactMemory(plan.revision)}){Text("Compact")}},dismissButton={TextButton(onClick={vm.dismissCompact()}){Text("Cancel")}}) }
}
