const MAX_CHUNK_LENGTH = 1800;
const REQUEST_DELAY_MS = 300;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function chunkText(text: string, maxLen: number): string[] {
  if (text.length <= maxLen) return [text];
  const chunks: string[] = [];
  let remaining = text;
  while (remaining.length > maxLen) {
    let splitAt = remaining.lastIndexOf(' ', maxLen);
    if (splitAt <= 0) splitAt = maxLen;
    chunks.push(remaining.slice(0, splitAt));
    remaining = remaining.slice(splitAt).trimStart();
  }
  if (remaining.length > 0) chunks.push(remaining);
  return chunks;
}

async function translateChunk(text: string, targetLang: string): Promise<string> {
  const url =
    'https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=' +
    encodeURIComponent(targetLang) +
    '&dt=t&q=' +
    encodeURIComponent(text);

  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Çeviri isteği başarısız: ${res.status}`);
  }
  const json = (await res.json()) as any[];
  const segments = json?.[0] ?? [];
  return segments.map((segment: any[]) => segment[0]).join('');
}

export async function translateText(text: string, targetLang = 'tr'): Promise<string> {
  const trimmed = text?.trim();
  if (!trimmed) return text ?? '';

  const chunks = chunkText(trimmed, MAX_CHUNK_LENGTH);
  const translated: string[] = [];

  for (const chunk of chunks) {
    try {
      translated.push(await translateChunk(chunk, targetLang));
    } catch (err) {
      console.error('Çeviri hatası, orijinal metin kullanılacak:', (err as Error).message);
      translated.push(chunk);
    }
    if (chunks.length > 1) await sleep(REQUEST_DELAY_MS);
  }

  return translated.join('');
}
