package com.atlas.ai.feature.files

import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.atlas.ai.domain.model.UiState
import com.atlas.ai.navigation.AtlasViewModel
import com.atlas.ai.ui.theme.*

@Composable internal fun FilesScreen(s: UiState, vm: AtlasViewModel) {
 val context=LocalContext.current
 var uploadUri by remember { mutableStateOf<Uri?>(null) }
 var name by rememberSaveable { mutableStateOf("") }
 var downloadPath by rememberSaveable { mutableStateOf("") }
 val upload=rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
  if(uri != null) {
   uploadUri=uri
   name="upload.txt"
   runCatching { context.contentResolver.query(uri,arrayOf(OpenableColumns.DISPLAY_NAME),null,null,null)?.use { cursor ->
    if(cursor.moveToFirst()) name=cursor.getString(0).orEmpty().take(120)
   } }
  }
 }
 val download=rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { uri ->
  if(uri != null && downloadPath.isNotBlank()) vm.downloadFile(downloadPath,uri)
 }
 LazyColumn(Modifier.fillMaxSize().padding(20.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
  item { Heading("Your workspace",if(s.demo) "Sample files · connect to manage files" else "${s.fileDirectory.ifEmpty { "Server files" }} · uploads up to 5 MiB") }
  item { Text("Workspace files support upload and text editing. Agent, memory and backups are read-only here; use Memory to change facts.",color=Muted) }
  item { Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
   if(s.fileDirectory.isNotEmpty()) TextButton(enabled=!s.busy,onClick={vm.listFiles("")}) { Text("Back") }
   TextButton(enabled=!s.busy,onClick={vm.listFiles(s.fileDirectory)}) { Text("Refresh") }
   Button(enabled=!s.demo && !s.busy,onClick={upload.launch("*/*")}) { Text("Upload") }
  } }
  items(s.files,key={it.path}) { file -> AtlasCard {
   Text(file.name,style=MaterialTheme.typography.titleMedium)
   Text(if(file.directory) "Folder" else "${file.size_bytes} bytes · ${if(file.writable) "Editable workspace file" else "Read-only"}",color=Muted)
   Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
    TextButton(enabled=!s.demo && !s.busy,onClick={if(file.directory) vm.listFiles(file.path) else vm.openFile(file.path)}) { Text(if(file.directory) "Open folder" else "Open text") }
    if(!file.directory) TextButton(enabled=!s.demo && !s.busy,onClick={downloadPath=file.path;download.launch(file.name)}) { Text("Download") }
   }
  } }
  if(s.files.isEmpty() && !s.busy) item { Text("This folder is empty.",color=Muted) }
 }
 uploadUri?.let { uri -> AlertDialog(onDismissRequest={uploadUri=null},title={Text("Upload to workspace")},text={Column {
  Text("Choose a new filename. Existing files will never be overwritten by an upload.")
  OutlinedTextField(name,{name=it.take(120)},label={Text("Filename")},singleLine=true)
 }},confirmButton={TextButton(enabled=name.isNotBlank() && !s.busy,onClick={vm.uploadFile(uri,name);uploadUri=null}){Text("Upload")}},dismissButton={TextButton(onClick={uploadUri=null}){Text("Cancel")}}) }
 s.document?.let { doc ->
  var text by rememberSaveable(doc.path,doc.revision) { mutableStateOf(doc.content) }
  var discard by remember { mutableStateOf(false) }
  val close={if(text != doc.content) discard=true else vm.closeFile()}
  Dialog(onDismissRequest={if(!s.busy) close()},properties=DialogProperties(usePlatformDefaultWidth=false)) {
   Surface(Modifier.fillMaxSize(),color=MaterialTheme.colorScheme.background) { Column(Modifier.fillMaxSize().padding(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
    Text(doc.path,style=MaterialTheme.typography.titleMedium)
    Text(if(doc.writable) "UTF-8 text editor · 256 KiB maximum" else "Read-only document",color=Muted)
    s.error?.let { Text(it,color=MaterialTheme.colorScheme.error) }
    s.notice?.let { Text(it,color=Cyan) }
    OutlinedTextField(text,{if(doc.writable) text=it.take(262144)},readOnly=!doc.writable,modifier=Modifier.fillMaxWidth().weight(1f))
    Row(horizontalArrangement=Arrangement.spacedBy(12.dp)) {
     TextButton(enabled=!s.busy,onClick={close()}) { Text("Close") }
     if(doc.writable) Button(enabled=!s.busy && text != doc.content,onClick={vm.saveFile(doc.path,text,doc.revision)}) { Text("Save") }
    }
   } }
  }
  if(discard) AlertDialog(onDismissRequest={discard=false},title={Text("Discard unsaved changes?")},confirmButton={TextButton(onClick={discard=false;vm.closeFile()}){Text("Discard")}},dismissButton={TextButton(onClick={discard=false}){Text("Keep editing")}})
 }
}
