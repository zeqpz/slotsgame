// Reading books files. Slot Engine writes books_<mode>.jsonl.zst as a chain of zstd frames (one per chunk, each
// followed by an empty frame); Node's zstd decompressor stops at the end of the first frame, so the file is split
// into frames here and each one is streamed through its own decompressor.
import fs from "fs"
import readline from "readline"
import { Readable } from "stream"
import zlib from "zlib"

/** The frames of a zstd file (skippable frames dropped). */
export function zstdFrames(buf: Buffer): Buffer[] {
  const frames: Buffer[] = []
  let off = 0
  while (off < buf.length) {
    const magic = buf.readUInt32LE(off)
    if (magic >>> 4 === 0x184d2a5) {
      off += 8 + buf.readUInt32LE(off + 4) // skippable frame
      continue
    }
    if (magic !== 0xfd2fb528) throw new Error(`not a zstd frame at byte ${off}`)
    const start = off
    let p = off + 4
    const fhd = buf[p++]!
    const single = (fhd >> 5) & 1
    if (!single) p += 1 // window descriptor
    p += [0, 1, 2, 4][fhd & 3]! // dictionary id
    p += [single ? 1 : 0, 2, 4, 8][fhd >> 6]! // frame content size
    for (;;) {
      const header = buf[p]! | (buf[p + 1]! << 8) | (buf[p + 2]! << 16)
      p += 3
      const type = (header >> 1) & 3
      p += type === 1 ? 1 : header >>> 3 // RLE blocks hold one byte
      if (header & 1) break // last block
    }
    if ((fhd >> 2) & 1) p += 4 // content checksum
    frames.push(buf.subarray(start, p))
    off = p
  }
  return frames
}

/** Every line of a books file (.jsonl.zst across all its frames, or plain .jsonl). */
export async function* bookLines(file: string): AsyncGenerator<string> {
  const frames = file.endsWith(".zst") ? zstdFrames(fs.readFileSync(file)) : null
  const count = frames ? frames.length : 1
  for (let i = 0; i < count; i++) {
    const input = frames ? Readable.from([frames[i]!], { objectMode: false }).pipe(zlib.createZstdDecompress()) : fs.createReadStream(file)
    const rl = readline.createInterface({ input, crlfDelay: Infinity })
    for await (const line of rl) if (line.trim()) yield line
  }
}
