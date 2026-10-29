package com.atlas.ai.core.network

import java.io.InputStream
import java.io.ByteArrayOutputStream

object BoundedFiles {
 fun read(input: InputStream, limit: Int): ByteArray {
  val out = ByteArrayOutputStream()
  val buffer = ByteArray(8192)
  while(true) {
   val count = input.read(buffer)
   if(count < 0) break
   require(out.size() + count <= limit) { "File exceeds the 5 MiB limit." }
   out.write(buffer,0,count)
  }
  return out.toByteArray()
 }
}
