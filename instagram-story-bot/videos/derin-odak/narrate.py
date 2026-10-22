"""Derin Odak videosunu ElevenLabs ile seslendirir.

Gerekenler:
  ELEVENLABS_API_KEY   ortam değişkeni (zorunlu)
  ELEVENLABS_VOICE_ID  ortam değişkeni (isteğe bağlı, varsayılan: Adam)

Kullanım:
  python3 narrate.py                     -> derin-odak-sesli.mp4
"""
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.join(HERE, "derin-odak.mp4")
OUT = os.path.join(HERE, "derin-odak-sesli.mp4")
WORK = os.path.join(HERE, ".tts")

VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
MODEL = "eleven_multilingual_v2"

# (başlangıç sn, bitmesi gereken sn, metin) — altyazı zamanlarıyla aynı
LINES = [
    (0.3, 6.9, "Telefonuna gelen tek bir bildirime bakmak üç saniye sürer."),
    (7.2, 15.8, "Ama beyninin böldüğün işe aynı derinlikte geri dönmesi, tam yirmi üç dakika on beş saniye sürer."),
    (16.2, 24.8, "Günde on kez bölünürsen, bütün gün çalışıp hiçbir şey üretememiş hissedersin."),
    (25.2, 28.6, "Zamanını değil, dikkatini koru."),
    (28.7, 33.5, "Odaklanmakta zorlanan bir arkadaşına gönder."),
]


def tts(text, path):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY tanımlı değil.")
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128",
        data=json.dumps({
            "text": text,
            "model_id": MODEL,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True},
        }).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", path])
    return float(out)


def main():
    os.makedirs(WORK, exist_ok=True)
    inputs, filters = [], []
    for i, (start, end, text) in enumerate(LINES):
        p = os.path.join(WORK, f"line{i}.mp3")
        if not os.path.exists(p):
            print(f"seslendiriliyor: {text}")
            tts(text, p)
        d = duration(p)
        room = end - start
        tempo = min(1.18, max(1.0, d / room))  # sığmazsa en fazla %18 hızlandır
        if d / tempo > room:
            print(f"uyarı: satır {i + 1} {d / tempo - room:.1f} sn taşıyor")
        inputs += ["-i", p]
        filters.append(f"[{i + 1}:a]atempo={tempo:.3f},adelay={int(start * 1000)}|{int(start * 1000)}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(LINES)))
    filters.append(f"{mix}amix=inputs={len(LINES)}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    # son satır video bitince kesilmesin diye son kareyi gerektiği kadar uzat
    vlen = duration(VIDEO)
    tail = max(0.0, LINES[-1][1] - vlen)
    vf = f"[0:v]tpad=stop_mode=clone:stop_duration={tail:.2f}[vout]"
    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error", "-i", VIDEO, *inputs,
        "-filter_complex", ";".join([vf] + filters),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT,
    ])
    print(f"hazır: {OUT}")


if __name__ == "__main__":
    main()
