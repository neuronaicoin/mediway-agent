"""
================================================================
 MEDIWAY AGENT — REELS VİDEO ÜRETİCİ
 (reel_maker.py)
================================================================

Verilen örnek videonun üstüne, AI'ın ürettiği hook metnini basar.
ffmpeg drawtext filtresi kullanır (Pillow video yapamaz).

  - Metin üst-orta bölgeye, yarı saydam koyu şerit üstüne basılır
  - Türkçe karakterler DejaVu fontla düzgün çıkar
  - Çıktı Instagram/Facebook Reels uyumlu (dikey, h264)

Gerektirir:  ffmpeg kurulu olmalı  (apt install ffmpeg)
================================================================
"""

import os
import re
import subprocess
import textwrap
import glob


def _find_font():
    """DejaVu Bold fontunu otomatik bul (Railway/Linux/Mac farklı yerlerde)."""
    name = "DejaVuSans-Bold.ttf"
    for pat in [
        f"/usr/share/fonts/truetype/dejavu/{name}",
        f"/usr/share/fonts/dejavu/{name}",
        f"/usr/share/fonts/**/{name}",
        f"/nix/**/{name}",
        f"/System/Library/Fonts/Supplemental/{name}",
    ]:
        hits = glob.glob(pat, recursive=True)
        if hits:
            return hits[0]
    return name


FONT_BOLD = _find_font()


def _escape_drawtext(text):
    """ffmpeg drawtext için özel karakterleri kaçır."""
    # Emoji temizle (videoda da tofu olmasın)
    emoji_pattern = re.compile(
        "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002190-\U000021FF\U00002B00-\U00002BFF\uFE0F]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text).strip()
    # drawtext'te tehlikeli karakterleri kaçır
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\u2019")   # tek tırnağı tipografik apostrofa çevir
    text = text.replace("%", "\\%")
    return text


def _wrap_text(text, width=24):
    """Metni satırlara böl (videoda taşmasın). ffmpeg satır sonu için \n kullanır."""
    lines = textwrap.wrap(text, width=width)
    return "\n".join(lines)


def make_reel(video_path, screen_text, output_path,
              font_size=46, y_position="h*0.14"):
    """
    Videonun üstüne metin basıp yeni video üretir.

    video_path:   kaynak örnek video
    screen_text:  basılacak metin (AI hook)
    output_path:  çıktı video yolu
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video bulunamadı: {video_path}")

    # Çıktı klasörü yoksa oluştur
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Dar dikey videolarda (576px) taşmayı önlemek için kısa satırlar
    wrapped = _wrap_text(_escape_drawtext(screen_text), width=18)

    # drawtext filtresi:
    #  - yarı saydam koyu kutu (box) metnin arkasında okunabilirlik için
    #  - beyaz metin, kalın font, üst-orta hizalı
    drawtext = (
        f"drawtext="
        f"fontfile={FONT_BOLD}:"
        f"text='{wrapped}':"
        f"fontcolor=white:"
        f"fontsize={font_size}:"
        f"line_spacing=14:"
        f"box=1:boxcolor=black@0.55:boxborderw=30:"
        f"x=(w-text_w)/2:"
        f"y={y_position}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", drawtext,
        "-codec:a", "copy",          # sesi olduğu gibi koru
        "-codec:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",       # IG/FB uyumluluğu
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg hatası:\n{result.stderr[-800:]}")

    return output_path


# ----------------------------------------------------------------
# TEST
# ----------------------------------------------------------------
if __name__ == "__main__":
    import glob
    os.makedirs("output_videos", exist_ok=True)

    sample = None
    for cand in ["1video.mp4", "2video.mp4"]:
        if os.path.exists(cand):
            sample = cand
            break
    if not sample:
        vids = glob.glob("*.mp4")
        sample = vids[0] if vids else None

    if not sample:
        print("⚠️  Test için video bulunamadı (klasöre .mp4 koy).")
    else:
        out = make_reel(
            sample,
            "Rakibiniz o aramada çıkıyor. Ya siz?",
            "output_videos/reel_test.mp4",
        )
        print(f"✅ Reel üretildi: {out}")
        print(f"   Kaynak: {sample}")