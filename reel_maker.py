"""
================================================================
 GÜZELLİKADRESİN AGENT — ANİMASYONLU METİN-REELS ÜRETİCİ
 (reel_maker.py)
================================================================
Sıfırdan, marka temalı animasyonlu dikey video (Reels) üretir.
Örnek videoya İHTİYAÇ YOK. Sessiz (kullanıcı sonra müzik ekler).
1080x1920 dikey, h264, Instagram/Facebook uyumlu.
================================================================
"""

import os
import re
import subprocess
import textwrap
import glob


def _find_font():
    name = "DejaVuSans-Bold.ttf"
    here = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(here, "fonts", name)
    if os.path.exists(local):
        return local
    for pat in [f"/usr/share/fonts/truetype/dejavu/{name}",
                f"/usr/share/fonts/dejavu/{name}",
                f"/usr/share/fonts/**/{name}", f"/nix/**/{name}"]:
        hits = glob.glob(pat, recursive=True)
        if hits:
            return hits[0]
    return name


FONT_BOLD = _find_font()
BG_COLOR = "0x0f202f"
ACCENT = "0xf5c518"
WHITE = "white"
W, H = 1080, 1920
DURATION = 8


def _escape(text):
    emoji = re.compile(
        "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
        "\U00002190-\U000021FF\U00002B00-\U00002BFF\uFE0F]+", flags=re.UNICODE)
    text = emoji.sub("", text).strip()
    text = text.replace("\\", "\\\\").replace(":", "\\:")
    text = text.replace("'", "\u2019").replace("%", "\\%")
    return text


def _wrap(text, width=18):
    return textwrap.wrap(text, width=width)


def make_reel(screen_text, output_path, subtitle=None):
    """Sıfırdan animasyonlu metin-reels üretir (sessiz)."""
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Metni başlık ve açıklama olarak ayır: "BAŞLIK\naçıklama cümlesi"
    # İlk satır = sarı büyük başlık, gerisi = beyaz açıklama (carousel ile aynı tarz)
    raw_parts = screen_text.split("\n", 1)
    title_part = _escape(raw_parts[0].strip())
    body_part = raw_parts[1].strip() if len(raw_parts) > 1 else ""

    title_lines = _wrap(title_part, width=16)
    body_lines = _wrap(_escape(body_part), width=18) if body_part else []

    filters = [f"drawbox=x=0:y=0:w={W}:h=14:color={ACCENT}:t=fill"]

    TITLE_SIZE = 100
    BODY_SIZE = 70
    title_h = 150
    body_h = 110
    total_h = len(title_lines) * title_h + len(body_lines) * body_h
    start_y = (H // 2) - (total_h // 2) - 60

    idx = 0
    y_cursor = start_y
    # Başlık satırları — SARI, büyük
    for line in title_lines:
        delay = 0.3 + idx * 0.35
        filters.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{line}':"
            f"fontcolor={ACCENT}:fontsize={TITLE_SIZE}:x=(w-text_w)/2:y={y_cursor}:"
            f"alpha='if(lt(t,{delay}),0,if(lt(t,{delay+0.5}),(t-{delay})/0.5,1))'"
        )
        y_cursor += title_h
        idx += 1
    # Açıklama satırları — BEYAZ
    for line in body_lines:
        delay = 0.3 + idx * 0.35
        filters.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{line}':"
            f"fontcolor={WHITE}:fontsize={BODY_SIZE}:x=(w-text_w)/2:y={y_cursor}:"
            f"alpha='if(lt(t,{delay}),0,if(lt(t,{delay+0.5}),(t-{delay})/0.5,1))'"
        )
        y_cursor += body_h
        idx += 1

    if subtitle:
        sub = _escape(subtitle)
        filters.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{sub}':"
            f"fontcolor={ACCENT}:fontsize=46:x=(w-text_w)/2:y={H-420}:"
            f"alpha='if(lt(t,1.5),0,if(lt(t,2.0),(t-1.5)/0.5,1))'"
        )

    filters.append(
        f"drawtext=fontfile={FONT_BOLD}:text='MediWay':"
        f"fontcolor={WHITE}:fontsize=52:x=(w-text_w)/2:y={H-280}"
    )
    filters.append(
        f"drawtext=fontfile={FONT_BOLD}:text='mediwayturkey.com':"
        f"fontcolor={ACCENT}:fontsize=40:x=(w-text_w)/2:y={H-200}"
    )

    vf = ",".join(filters)
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={BG_COLOR}:s={W}x{H}:d={DURATION}:r=30",
        "-vf", vf, "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg hatası:\n{result.stderr[-800:]}")
    return output_path


if __name__ == "__main__":
    os.makedirs("output_videos", exist_ok=True)
    out = make_reel(
        "Bölgenizdeki en iyi güzellik adresini anında bulun",
        "output_videos/reel_test.mp4",
        subtitle="Sağlık Turizmi",
    )
    print(f"✅ Animasyonlu reel üretildi: {out}")
