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
BG_COLOR = "0x2d508c"
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

    lines = _wrap(_escape(screen_text), width=18)
    filters = [f"drawbox=x=0:y=0:w={W}:h=14:color={ACCENT}:t=fill"]

    n = len(lines)
    line_h = 130
    total_h = n * line_h
    start_y = (H // 2) - (total_h // 2) - 60

    for i, line in enumerate(lines):
        delay = 0.3 + i * 0.35
        y = start_y + i * line_h
        filters.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{line}':"
            f"fontcolor={WHITE}:fontsize=88:x=(w-text_w)/2:y={y}:"
            f"alpha='if(lt(t,{delay}),0,if(lt(t,{delay+0.5}),(t-{delay})/0.5,1))'"
        )

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
