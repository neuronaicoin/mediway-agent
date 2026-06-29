"""
================================================================
 MEDIWAY AGENT — AI İÇERİK YAZARI (Claude Haiku)
 (ai_writer.py)
================================================================

Bu, agent'ın "düşünen beyni". content_generator'daki şablon
sisteminin yerine geçer (şablon, API çökerse fallback olarak kalır).

NE YAPAR:
  1. Anayasayı (content_constitution) Claude'a SİSTEM PROMPTU verir
  2. Performans verisini + ana amacı GİRDİ verir
  3. Claude O AN özgün içerik yazar (şablondan seçmez)
  4. Çıktıyı hard_rules'a göre DOĞRULAR (14 dil/klinik/ücretsiz/4 hashtag)
  5. Kural ihlali varsa Claude'a düzelttirir (retry)

"Dünyanın en iyi sosyal medya uzmanı gibi" davranış = bu dosyada.
Claude, ne tuttuğunu görür, tutmuş tarzı çoğaltır, tutmayanı bırakır.

----------------------------------------------------------------
GEREKİR:
  pip install anthropic
  ANTHROPIC_API_KEY environment variable (console.anthropic.com)
----------------------------------------------------------------
"""

import os
import re
import json

from content_constitution import CONSTITUTION

# Anthropic SDK — yoksa sistem fallback'e düşer (content_generator şablonu)
try:
    from anthropic import Anthropic
    _SDK_OK = True
except ImportError:
    _SDK_OK = False

# Model — tek satırda değiştirilebilir (Haiku ucuz+hızlı, Sonnet daha kaliteli)
MODEL = "claude-sonnet-4-6"   # Sonnet: daha akıllı, kaliteli içerik

API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Yasak ifadeler (güvenlik ağı — Claude'a ek olarak kod da kontrol eder)
FORBIDDEN_PATTERNS = [
    "ücretsiz", "bedava", "free", "ücretsizdir",
    "14 dil", "14 farklı dil", "14 dilde",
    "klinik",
    "malı katlıyor", "kapına", "tüm gelir senin",
    "kazancın erken biter", "almasına izin verme",
]
MAX_HASHTAGS = CONSTITUTION["content_style"]["max_hashtags"]


# ----------------------------------------------------------------
# SİSTEM PROMPTU — anayasayı Claude'un beynine yazar
# ----------------------------------------------------------------
def build_system_prompt():
    c = CONSTITUTION
    rules = "\n".join(f"- {r}" for r in c["hard_rules"])
    b2b = "\n".join(f"- {a}" for a in c["audience"]["primary_b2b"])
    props = "\n".join(f"- {v}" for v in c["brand"]["value_props"])

    return f"""Sen MediWay'in sosyal medya uzmanısın. Dünyanın en iyi sosyal medya \
stratejisti gibi davranıyorsun: veriye bakar, ne tuttuğunu görür, tutan tarzı \
çoğaltır, tutmayanı bırakırsın.

# ANA AMACIN
{c['mission']}

# MARKA
{c['brand']['name']} ({c['brand']['handle']}) — {c['brand']['website']}
{c['brand']['what_it_is']}

Değer önerileri:
{props}

# HEDEF KİTLE (B2B ÖNCELİK — bunları platforma ÜYE yapmak istiyoruz)
{b2b}

# İÇERİK TARZI
- Ton: POZİTİF, MOTİVE EDİCİ, profesyonel. Sağlayıcıyı küçük düşürmeden, \
ona fırsat ve kazanç gösteren bir dil kullan.
- Dil: Türkçe, akıcı ve kurumsal
- Yapı: dikkat çeken açılış → fırsatı göster → çözümü sun → net fayda → eyleme çağrı (üye ol)
- Öncelik metriği: BEĞENİ DEĞİL, kaydetme (saves) ve paylaşma (shares). İçeriği \
paylaşılası ve kaydedilesi yap.

# TON VE İFADE KURALLARI (ÇOK ÖNEMLİ)
ASLA şu kaba/yanlış ifadeleri veya benzerlerini kullanma:
- "malı katlıyor", "mal" gibi kaba ticari ifadeler
- "hasta kapına gelir", "kapına" — bunun yerine "size ulaşır", "sizi bulur"
- "tüm gelir senin", "kazancın senin" — bunun yerine "komisyon yok, kazancınız sizin"
- "kazancın erken biter", "para bitince" gibi olumsuz/tehdit edici ifadeler
- "rakiplerin almasına izin verme", "rakibin önde" gibi rekabet-korku dili
DOĞRU yaklaşım: pozitif fırsat dili. Örnekler:
- "Yerinizi alın, yabancı hastalara daha fazla görünün"
- "Uluslararası hastalar sizi kolayca bulsun"
- "Markanızı dünya sahnesine taşıyın"
- "Komisyon yok — gelen hasta tamamen sizin"

# SLAYT METNİ KURALI (ÇOK ÖNEMLİ — KISA VE VURUCU)
Her carousel slaytı KISA olmalı. Görsele sığması ve okunması için:
- Her slayt: VURUCU BİR BAŞLIK (1-3 kelime, BÜYÜK HARFLE) + altında TEK kısa cümle (en fazla 8-10 kelime).
- Başlık ile cümleyi ayırmak için araya \n koy. Örnek slayt:
  "ESTETİK\nYabancı hastalar sizi arıyor ama bulamıyor."
- Uzun paragraf, çok cümle, çok satır YAZMA. Slaytı kalabalıklaştırma.
- Toplam bir slayt 12 kelimeyi geçmesin. Kısa = güçlü = okunur.

# ZORUNLU: SİTE ADRESİ
Her caption'ın ve her story metninin SONUNA mutlaka şunu ekle (hashtag'lerden önce):
www.mediwayturkey.com

# KESİN KURALLAR (ASLA İHLAL ETME)
{rules}

# ÇIKTI FORMATI
Sadece geçerli JSON döndür, başka hiçbir şey yazma (markdown backtick yok, açıklama yok).
İstenen post tipine göre şu şemalardan biri:

CAROUSEL:
{{"type":"CAROUSEL","slides":[{{"slide":1,"text":"BAŞLIK\nkısa tek cümle hook"}},{{"slide":2,"text":"BAŞLIK\nkısa problem cümlesi"}},{{"slide":3,"text":"BAŞLIK\nkısa çözüm cümlesi"}},{{"slide":4,"text":"BAŞLIK\nkısa eyleme çağrı"}}],"caption":"açıklama metni + en fazla 4 hashtag"}}
Her slayt "text" alanı: BÜYÜK HARF BAŞLIK + \n + en fazla 8-10 kelimelik tek cümle. KISA TUT.

REELS:
{{"type":"REELS","screen_text":"videonun üstüne basılacak kısa güçlü metin (max ~80 karakter)","caption":"açıklama + eyleme çağrı + en fazla 4 hashtag"}}

STORY:
{{"type":"STORY","screen_text":"kısa story metni + 'üye ol link bio'da' çağrısı"}}

Hashtag KURALI: en fazla {MAX_HASHTAGS} adet. 'klinik', 'ücretsiz', '14 dil' ASLA geçmesin."""


# ----------------------------------------------------------------
# DOĞRULAMA — çıktı kurallara uyuyor mu?
# ----------------------------------------------------------------
def validate(content_dict):
    """Üretilen içerik hard_rules'a uyuyor mu? (ok, sebep) döner."""
    text = json.dumps(content_dict, ensure_ascii=False).lower()

    for bad in FORBIDDEN_PATTERNS:
        if bad in text:
            return False, f"yasak ifade: '{bad}'"

    # Hashtag sayısı kontrolü (caption + screen_text neredeyse)
    hashtags = re.findall(r"#\w+", json.dumps(content_dict, ensure_ascii=False))
    if len(hashtags) > MAX_HASHTAGS:
        return False, f"çok fazla hashtag: {len(hashtags)} (max {MAX_HASHTAGS})"

    return True, None


# ----------------------------------------------------------------
# JSON ÇIKAR — Claude bazen backtick/önsöz ekleyebilir, temizle
# ----------------------------------------------------------------
def _extract_json(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    # İlk { ve son } arasını al
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]
    return json.loads(raw)


# ----------------------------------------------------------------
# ANA ÜRETİM — Claude'a yazdır
# ----------------------------------------------------------------
def generate_post(post_type="carousel", performance_summary="", max_retries=3):
    """
    Claude Haiku ile özgün içerik üretir.
    performance_summary: learning_loop'tan gelen "ne tuttu" özeti (öğrenme).
    Hata/kural ihlali olursa şablona düşmek için ValueError fırlatır.
    """
    if not (_SDK_OK and API_KEY):
        raise RuntimeError("ANTHROPIC_API_KEY yok veya anthropic SDK kurulu değil")

    client = Anthropic(api_key=API_KEY)
    system = build_system_prompt()

    learning = ""
    if performance_summary:
        learning = (
            f"\n\n# SON PERFORMANS VERİSİ (buna göre adapte ol)\n"
            f"{performance_summary}\n"
            f"Tutmuş içeriğin tarzını/konusunu çoğalt, tutmayanı tekrar etme."
        )

    # A/B TESTİ (Aşama 4): Her üretimde farklı bir hook stili dene.
    import random as _r
    HOOK_STYLES = [
        "Çarpıcı bir SORU ile başla (okuyucuyu içine çeken).",
        "Şaşırtıcı bir İSTATİSTİK/gerçek ile başla.",
        "Yaygın bir HATA/yanlış inanışı vurgulayarak başla.",
        "Güçlü bir FAYDA vaadiyle başla (önce-sonra hissi).",
        "Kısa bir HİKAYE/senaryo ile başla (ilişki kurulabilir).",
    ]
    chosen_hook = _r.choice(HOOK_STYLES)

    user_msg = (
        f"Bir {post_type.upper()} içeriği üret. "
        f"B2B sağlayıcıları MediWay'e üye olmaya ikna et. "
        f"Özgün ol, daha önce ürettiklerini tekrarlama.\n"
        f"BU İÇERİĞİN HOOK STİLİ: {chosen_hook}{learning}"
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = "".join(
                block.text for block in resp.content if block.type == "text"
            )
            content = _extract_json(raw)

            ok, reason = validate(content)
            if ok:
                return content

            # Kural ihlali → Claude'a düzelttir
            last_error = reason
            user_msg = (
                f"Önceki çıktın kural ihlali içeriyordu ({reason}). "
                f"Düzelt ve yeniden {post_type.upper()} JSON üret. "
                f"'klinik', 'ücretsiz', '14 dil' kullanma, max {MAX_HASHTAGS} hashtag."
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            last_error = f"JSON parse hatası: {e}"
            user_msg = f"Geçerli JSON üretemedın. SADECE JSON döndür, {post_type.upper()} şemasında."

    raise ValueError(f"AI üretimi {max_retries} denemede başarısız: {last_error}")


# ----------------------------------------------------------------
# TEST
# ----------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 55)
    print(" AI WRITER — Claude Haiku içerik testi")
    print("=" * 55)
    if not (_SDK_OK and API_KEY):
        print("\n⚠️  ANTHROPIC_API_KEY ayarlı değil veya SDK kurulu değil.")
        print("   Bu makinede gerçek üretim testi yapılamaz.")
        print("   Claude Code'da (senin makinende) key varken çalışacak.")
        print("\n   Sistem promptu önizleme (ilk 600 karakter):")
        print("-" * 55)
        print(build_system_prompt()[:600] + " ...")
    else:
        for t in ["carousel", "reels", "story"]:
            print(f"\n── {t.upper()} ──")
            try:
                post = generate_post(t)
                print(json.dumps(post, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"  Hata: {e}")
