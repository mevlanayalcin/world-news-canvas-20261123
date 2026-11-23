import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const MAX_BYTES = 1_048_576;
const MAX_DIMENSION = 1024;
const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

interface PngSummary {
  width: number;
  height: number;
  bitDepth: number;
  colorType: number;
  chunkCount: number;
  idatBytes: number;
}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) {
      c = (c & 1) !== 0 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
})();

function computeCrc32(bytes: Buffer): number {
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) {
    crc = CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function inspectPngBuffer(data: Buffer): PngSummary {
  if (data.length === 0 || data.length > MAX_BYTES) {
    throw new Error(`PNG size out of bounds: ${data.length} bytes (max ${MAX_BYTES})`);
  }
  if (data.length < 33 || !data.subarray(0, 8).equals(PNG_SIGNATURE)) {
    throw new Error("Input file does not carry a valid PNG signature");
  }

  let cursor = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  let chunkCount = 0;
  let idatBytes = 0;
  let sawHeader = false;
  let sawEnd = false;

  while (cursor + 12 <= data.length) {
    const length = data.readUInt32BE(cursor);
    const kind = data.subarray(cursor + 4, cursor + 8).toString("ascii");
    const payloadStart = cursor + 8;
    const payloadEnd = payloadStart + length;
    const nextCursor = payloadEnd + 4;

    if (nextCursor > data.length) {
      throw new Error(`Truncated PNG chunk '${kind}' at byte ${cursor}`);
    }

    const expectedCrc = data.readUInt32BE(payloadEnd);
    const actualCrc = computeCrc32(data.subarray(cursor + 4, payloadEnd));
    if (actualCrc !== expectedCrc) {
      throw new Error(`CRC mismatch in PNG chunk '${kind}': expected 0x${expectedCrc.toString(16)}, got 0x${actualCrc.toString(16)}`);
    }

    if (chunkCount === 0) {
      if (kind !== "IHDR" || length !== 13) {
        throw new Error("First PNG chunk must be a 13-byte IHDR");
      }
      width = data.readUInt32BE(payloadStart);
      height = data.readUInt32BE(payloadStart + 4);
      bitDepth = data.readUInt8(payloadStart + 8);
      colorType = data.readUInt8(payloadStart + 9);
      sawHeader = true;
    } else if (kind === "IDAT") {
      idatBytes += length;
    }

    chunkCount += 1;
    cursor = nextCursor;

    if (kind === "IEND") {
      sawEnd = true;
      break;
    }
  }

  if (!sawHeader || !sawEnd || idatBytes === 0 || cursor !== data.length) {
    throw new Error("PNG stream is incomplete, lacks IDAT data, or has trailing bytes after IEND");
  }
  if (width <= 0 || height <= 0 || width > MAX_DIMENSION || height > MAX_DIMENSION) {
    throw new Error(`PNG dimensions ${width}x${height} exceed ${MAX_DIMENSION}x${MAX_DIMENSION}`);
  }
  if (bitDepth !== 8 || colorType !== 2) {
    throw new Error(`Expected 8-bit RGB PNG (bitDepth=8, colorType=2), got (${bitDepth}, ${colorType})`);
  }

  return { width, height, bitDepth, colorType, chunkCount, idatBytes };
}

function main(): void {
  const repoRoot = dirname(fileURLToPath(import.meta.url));
  const sourcePath = resolve(repoRoot, "entry.png");
  const outputDir = resolve(process.env.MAKEFUN_OUTPUT_DIR ?? "/output");
  const targetPath = join(outputDir, "entry.png");

  const imageBytes = readFileSync(sourcePath);
  inspectPngBuffer(imageBytes);

  mkdirSync(outputDir, { recursive: true });
  writeFileSync(targetPath, imageBytes);
}

main();
