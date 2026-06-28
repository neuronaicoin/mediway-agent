"""
================================================================
 MEDIWAY AGENT — GÖRSEL ÜRETİCİ (CAROUSEL + STORY)
 (image_maker.py)
================================================================

Üretilen metni marka kimliğinde görsele basar.
  - Carousel: 1080x1080 kare (mevcut)
  - Story:    1080x1920 dikey (YENİ)

Gerektirir:  pip install pillow
================================================================
"""

from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
import re
import glob


def _find_font(bold=True):
    """DejaVu fontunu bul. ÖNCE repo içindeki fonts/ klasörü (Railway'de garantili)."""
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    # 1) Repo içindeki fonts/ klasörü — bu dosyanın yanında (en güvenilir)
    here = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(here, "fonts", name)
    if os.path.exists(local):
        return local
    # 2) Sistemde ara (lokal geliştirme için)
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/{name}",
        f"/usr/share/fonts/dejavu/{name}",
        f"/usr/share/fonts/**/{name}",
        f"/nix/**/{name}",
        f"/System/Library/Fonts/Supplemental/{name}",
    ]
    for pat in candidates:
        hits = glob.glob(pat, recursive=True)
        if hits:
            return hits[0]
    return None


FONT_BOLD = _find_font(bold=True) or "DejaVuSans-Bold.ttf"
FONT_REG = _find_font(bold=False) or "DejaVuSans.ttf"


def strip_emoji(text):
    """DejaVu fontu emoji basamıyor (tofu çıkar). Madde emojilerini • yap, gerisini sil."""
    # Madde/onay işaretlerini font-safe • ile değiştir
    for bullet in ["✅", "☑️", "✔️", "✔", "•", "👉", "➡️", "→"]:
        text = text.replace(bullet, "•") if bullet in ["✅", "☑️", "✔️", "✔"] else text.replace(bullet, "")
    # Kalan tüm emoji/süs sembollerini sil
    emoji_pattern = re.compile(
        "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002190-\U000021FF\U00002B00-\U00002BFF\uFE0F]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    # Satır içi çoklu boşlukları tek boşluğa indir (newline'ları KORU)
    lines = [re.sub(r"[ \t]{2,}", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines).strip()

BRAND = {
    "bg_color": (15, 32, 47),        # koyu lacivert
    "accent_color": (245, 197, 24),  # sarı vurgu
    "text_color": (255, 255, 255),   # beyaz
    "size": (1080, 1080),            # carousel kare
    "story_size": (1080, 1920),      # story dikey
    "handle": "www.mediwayturkey.com",
}

FONT_BOLD = _find_font(bold=True) or "DejaVuSans-Bold.ttf"
FONT_REG = _find_font(bold=False) or "DejaVuSans.ttf"


def make_slide(text, filename, slide_num=None, total=None):
    """Carousel slaytı (1080x1080 PNG)."""
    W, H = BRAND["size"]
    img = Image.new("RGB", (W, H), BRAND["bg_color"])
    draw = ImageDraw.Draw(img)

    text = strip_emoji(text)

    char_count = len(text)
    if char_count < 60:
        font_size = 64
    elif char_count < 120:
        font_size = 52
    else:
        font_size = 42
    font = ImageFont.truetype(FONT_BOLD, font_size)

    wrap_width = max(18, int(W / (font_size * 0.62)))
    # Newline'lara saygı duy: her paragrafı ayrı sar
    lines = []
    for para in text.split("\n"):
        if para.strip() == "":
            lines.append("")
        else:
            lines.extend(textwrap.wrap(para, width=wrap_width))
    line_height = font_size + 18
    total_text_h = len(lines) * line_height
    y = (H - total_text_h) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (W - line_w) // 2
        draw.text((x, y), line, font=font, fill=BRAND["text_color"])
        y += line_height

    small_font = ImageFont.truetype(FONT_REG, 32)
    handle = BRAND["handle"]
    hb = draw.textbbox((0, 0), handle, font=small_font)
    draw.text(((W - (hb[2]-hb[0])) // 2, H - 80), handle,
              font=small_font, fill=BRAND["accent_color"])

    if slide_num and total:
        page = f"{slide_num}/{total}"
        pb = draw.textbbox((0, 0), page, font=small_font)
        draw.text((W - (pb[2]-pb[0]) - 50, 50), page,
                  font=small_font, fill=BRAND["accent_color"])

    img.save(filename, "PNG")
    return filename


def make_story_slide(text, filename):
    """Story görseli (1080x1920 dikey PNG). Metin ortada, altta CTA + handle."""
    W, H = BRAND["story_size"]
    img = Image.new("RGB", (W, H), BRAND["bg_color"])
    draw = ImageDraw.Draw(img)

    text = strip_emoji(text)

    # Üstte ince sarı aksan şerit
    draw.rectangle([0, 0, W, 12], fill=BRAND["accent_color"])

    margin = 90
    usable_w = W - 2 * margin

    char_count = len(text)
    if char_count < 80:
        font_size = 72
    elif char_count < 160:
        font_size = 58
    else:
        font_size = 46
    font = ImageFont.truetype(FONT_BOLD, font_size)

    # Genişliğe göre güvenli sarma (piksel ölçerek)
    def wrap_to_width(s, fnt, max_w):
        words = s.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=fnt) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    lines = wrap_to_width(text, font, usable_w)
    line_height = font_size + 22
    total_text_h = len(lines) * line_height
    y = (H - total_text_h) // 2 - 120

    for line in lines:
        draw.text((margin, y), line, font=font, fill=BRAND["text_color"])
        y += line_height

    # Alt CTA kutusu (sarı zemin, lacivert yazı)
    cta_text = "Üye ol  •  link bio'da"
    cta_font = ImageFont.truetype(FONT_BOLD, 44)
    cb = draw.textbbox((0, 0), cta_text, font=cta_font)
    cta_w = cb[2] - cb[0]
    box_pad = 40
    box_x0 = (W - cta_w) // 2 - box_pad
    box_y0 = H - 360
    box_x1 = (W + cta_w) // 2 + box_pad
    box_y1 = box_y0 + 100
    draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=24,
                           fill=BRAND["accent_color"])
    draw.text(((W - cta_w) // 2, box_y0 + 26), cta_text,
              font=cta_font, fill=BRAND["bg_color"])

    # En altta handle
    small_font = ImageFont.truetype(FONT_REG, 36)
    hb = draw.textbbox((0, 0), BRAND["handle"], font=small_font)
    draw.text(((W - (hb[2]-hb[0])) // 2, H - 110), BRAND["handle"],
              font=small_font, fill=BRAND["accent_color"])

    img.save(filename, "PNG")
    return filename


def make_carousel(slides, output_dir="output_images", prefix="carousel"):
    """Carousel'in tüm slaytlarını görsele döker."""
    os.makedirs(output_dir, exist_ok=True)
    files = []
    total = len(slides)
    for i, slide in enumerate(slides, 1):
        text = slide["text"] if isinstance(slide, dict) else slide
        fname = os.path.join(output_dir, f"{prefix}_slide{i}.png")
        make_slide(text, fname, slide_num=i, total=total)
        files.append(fname)
    return files


def make_story(text, output_dir="output_images", prefix="story"):
    """Tek story görseli üretir."""
    os.makedirs(output_dir, exist_ok=True)
    fname = os.path.join(output_dir, f"{prefix}.png")
    make_story_slide(text, fname)
    return fname


# ----------------------------------------------------------------
# TEST
# ----------------------------------------------------------------
if __name__ == "__main__":
    try:
        from content_generator import generate_post
        post = generate_post("carousel")
        slides = post["slides"]
        story = generate_post("story")
        story_text = story["screen_text"]
    except Exception:
        slides = [
            {"text": "İstanbul'da saç ekimi yapıyorsunuz. Peki yurt dışındaki hasta sizi nasıl bulacak?"},
            {"text": "Listede yoksanız, o hasta sizi hiç göremez."},
            {"text": "MediWay ile değişir: Hasta direkt size ulaşır, komisyon yok."},
            {"text": "Yerinizi alın 👉 link bio'da"},
        ]
        story_text = "Rakibiniz o aramada çıkıyor. Ya siz?"

    files = make_carousel(slides)
    print("Carousel görselleri:")
    for f in files:
        print(f"  ✅ {f}")
    sf = make_story(story_text)
    print(f"Story görseli:\n  ✅ {sf}")