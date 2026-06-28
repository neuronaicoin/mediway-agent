"""
================================================================
 MEDIWAY AGENT — İÇERİK ÜRETİCİ (AI + ŞABLON FALLBACK)
 (content_generator.py)
================================================================

Bu modül artık İKİ KATMANLI çalışır:

  1. ÖNCE: ai_writer (Claude Haiku) ile ÖZGÜN içerik üretmeyi dener.
     → "Dünyanın en iyi sosyal medya uzmanı" davranışı burada.

  2. API çökerse / key yoksa / kota biterse: ŞABLON fallback devreye
     girer. Sistem ASLA durmaz — her zaman içerik üretir.

Şablon da düzeltildi: '14 dil' ve 'klinik' kaldırıldı, max 4 hashtag.

Çalıştırmak için:  python content_generator.py
================================================================
"""

import random

# AI katmanı (varsa kullan, yoksa şablona düş)
try:
    from ai_writer import generate_post as ai_generate_post
    _AI_AVAILABLE = True
except Exception:
    _AI_AVAILABLE = False


# ----------------------------------------------------------------
# ŞABLON HAVUZLARI (FALLBACK — AI çalışmazsa)
# ----------------------------------------------------------------
CITIES_LOC = {
    "İstanbul": "İstanbul'da", "İzmir": "İzmir'de", "Antalya": "Antalya'da",
    "Ankara": "Ankara'da", "Kapadokya": "Kapadokya'da", "Bursa": "Bursa'da",
}
CITIES = list(CITIES_LOC.keys())
TREATMENTS = ["saç ekimi", "diş tedavisi", "estetik cerrahi", "estetik işlemler"]
TARGETS = ["sağlık kuruluşunuz", "hastaneniz", "saç ekim merkeziniz",
           "muayenehaneniz", "merkeziniz"]
SEARCH_TERMS = {
    "saç ekimi": "hair transplant Turkey", "diş tedavisi": "dental Turkey",
    "estetik cerrahi": "plastic surgery Turkey", "estetik işlemler": "aesthetic Turkey",
}

HOOKS = [
    "{city_loc} {treatment} yapıyorsunuz. Peki yurt dışındaki hasta sizi nasıl bulacak?",
    "Bir hasta '{search}' diye aradığında karşısına siz mi çıkıyorsunuz, rakibiniz mi?",
    "{target_cap} en iyi tedaviyi sunuyor. Ama hasta sizi tanımıyorsa, sizin için yoksunuz demektir.",
    "Rakibiniz o aramada çıkıyor. Ya siz?",
    "Reklam durduğu an, hasta akışınız da duruyor. Tanıdık geldi mi?",
    "{city_loc} yüzlerce sağlayıcı var. Yabancı hasta neden sizi seçsin — sizi bulabilirse tabii.",
]
BODIES = [
    "Her yıl yüz binlerce yabancı hasta {treatment} için Türkiye'yi araştırıyor. "
    "Hepsi önce Google'da, AI arama motorlarında bakıyor. O aramada görünmek artık bir tercih değil.",
    "Listede yoksanız, o hasta sizi hiç göremez — doğruca başka bir sağlayıcının sayfasına gider.",
    "Reklam = kiralık trafik. Para bitince görünürlük de biter. Aracılar ise her hastadan pay alıyor.",
    "Yurt dışından gelen hasta sizi internette bulamıyorsa, ne kadar iyi olduğunuzun bir önemi kalmıyor.",
]
BENEFITS = [
    "✅ Hasta doğrudan size ulaşır — aracı yok",
    "✅ Komisyon yok — gelen hasta tamamen sizin",
    "✅ Yapay zekâ destekli hasta eşleştirme",
    "✅ Dünyanın her yerinden yabancı hasta erişimi",
    "✅ SEO + AI arama gücüyle kalıcı görünürlük",
]
CTAS = [
    "Erken üyeler avantajlı koşullardan yararlanıyor. Yerinizi alın 👉 link bio'da",
    "O aramada siz çıkın. Üye olun 👉 mediwayturkey.com",
    "Yerinizi alın — link bio'da 👉 mediwayturkey.com",
    "Kalıcı görünürlük için yerinizi alın 👉 link bio'da",
]
HASHTAGS = [
    "#sağlıkturizmi", "#medikalturizm", "#healthtourism",
    "#saçekimi", "#diştedavisi", "#estetik",
    "#hairtransplantturkey", "#sağlıkkuruluşu", "#plastikcerrahi",
]

# Güvenlik ağı (şablon için)
FORBIDDEN = ["ücretsiz", "bedava", "free", "ücretsizdir", "14 dil", "klinik",
             "malı katlıyor", "kapına", "tüm gelir senin",
             "kazancın erken biter", "almasına izin verme"]
MAX_HASHTAGS = 4


def check_rules(text):
    low = text.lower()
    for word in FORBIDDEN:
        if word in low:
            return False, word
    return True, None


# ----------------------------------------------------------------
# ŞABLON ÜRETİM (fallback)
# ----------------------------------------------------------------
def _template_post(post_type="carousel"):
    city = random.choice(CITIES)
    city_loc = CITIES_LOC[city]
    treatment = random.choice(TREATMENTS)
    target = random.choice(TARGETS)
    search = SEARCH_TERMS.get(treatment, "Turkey")

    hook = random.choice(HOOKS).format(
        city=city, city_loc=city_loc, treatment=treatment,
        target_cap=target.capitalize(), search=search,
    )
    body = random.choice(BODIES).format(treatment=treatment, city=city)
    benefits = "\n".join(random.sample(BENEFITS, 3))
    cta = random.choice(CTAS)
    tags = " ".join(random.sample(HASHTAGS, MAX_HASHTAGS))  # max 4

    if post_type == "carousel":
        content = {
            "type": "CAROUSEL",
            "slides": [
                {"slide": 1, "text": hook},
                {"slide": 2, "text": body},
                {"slide": 3, "text": "MediWay ile değişir:\n" + benefits},
                {"slide": 4, "text": cta},
            ],
            "caption": f"{hook}\n\nwww.mediwayturkey.com\n\n{tags}",
        }
    elif post_type == "reels":
        content = {
            "type": "REELS",
            "screen_text": hook,
            "caption": f"{body}\n\n{cta}\n\nwww.mediwayturkey.com\n\n{tags}",
        }
    else:  # story
        content = {
            "type": "STORY",
            "screen_text": f"{hook}\n\nÜye ol, link bio'da\nwww.mediwayturkey.com",
        }

    ok, _ = check_rules(str(content))
    if not ok:
        return _template_post(post_type)
    return content


# ----------------------------------------------------------------
# ANA ÜRETİM — önce AI, sonra şablon
# ----------------------------------------------------------------
def generate_post(post_type="carousel", performance_summary=""):
    """
    Önce Claude Haiku ile özgün üretir; başarısız olursa şablona düşer.
    Sistem her durumda içerik döndürür.
    """
    if _AI_AVAILABLE:
        try:
            return ai_generate_post(post_type, performance_summary)
        except Exception as e:
            print(f"  ⚠️  AI üretimi başarısız ({e}) → şablona geçiliyor")
    return _template_post(post_type)


def generate_daily_plan(performance_summary=""):
    return {
        "carousels": [generate_post("carousel", performance_summary) for _ in range(2)],
        "reels": [generate_post("reels", performance_summary) for _ in range(2)],
        "stories": [generate_post("story", performance_summary) for _ in range(5)],
    }


# ----------------------------------------------------------------
# GÖSTERİM
# ----------------------------------------------------------------
def print_plan(plan):
    print("=" * 58)
    print(" MEDIWAY AGENT — BUGÜNÜN İÇERİK PLANI")
    print("=" * 58)
    print("\n📑 CAROUSEL'LER\n" + "-" * 40)
    for i, c in enumerate(plan["carousels"], 1):
        print(f"\n  ── Carousel {i} ──")
        for s in c["slides"]:
            print(f"  [Slayt {s['slide']}] {s['text']}")
        print(f"  Açıklama: {c['caption']}")
    print("\n\n🎬 REELS\n" + "-" * 40)
    for i, r in enumerate(plan["reels"], 1):
        print(f"\n  ── Reels {i} ──")
        print(f"  Ekran metni: {r['screen_text']}")
        print(f"  Açıklama: {r.get('caption','')}")
    print("\n\n📱 STORY'LER\n" + "-" * 40)
    for i, st in enumerate(plan["stories"], 1):
        print(f"  [Story {i}] {st['screen_text']}")
    print("\n" + "=" * 58)


if __name__ == "__main__":
    mode = "AI (Claude Haiku)" if _AI_AVAILABLE else "ŞABLON (AI yok)"
    print(f"Üretim modu: {mode}\n")
    daily = generate_daily_plan()
    print_plan(daily)
