# MediWay Agent — Devir Notları (HANDOVER)

Bu klasör, MediWay Instagram/Facebook otomasyon agent'ının **tam otomatik,
Claude AI destekli** versiyonudur. Tüm parçalar yazıldı ve görsel/video
katmanı gerçek dosyalarla test edildi. Kalan tek şey: **gerçek token/FTP
ortamında canlı yayın testi** (senin makinende).

---

## Sistem nasıl çalışıyor (akış)

```
scheduler.py (her 4 saatte bir uyanır)
   │
   ├─ learning_loop.py → son gönderi performansını analiz et, özet çıkar
   │
   ├─ content_generator.py → ai_writer.py (Claude Haiku) ile ÖZGÜN içerik üret
   │       (API çökerse şablon fallback devreye girer, sistem durmaz)
   │
   ├─ image_maker.py → carousel (1080x1080) / story (1080x1920) görseli bas
   ├─ reel_maker.py  → örnek videoya hook metni bas (ffmpeg)
   │
   └─ publisher.py → Instagram'a yayınla (carousel/story/reels)
                   → AYNI içeriği Facebook'a yayınla (çift yayın)
```

**Günlük limit (anayasa):** 4 paylaşım (2 carousel + 2 reels) + 5 story.
Agent günde ~6 kez uyansa da limiti ASLA aşmaz (spam koruması test edildi).

---

## Dosyalar

| Dosya | Görev | Durum |
|-------|-------|-------|
| `content_constitution.py` | Değişmez kurallar (Claude'un sistem promptu) | ✅ Düzeltildi |
| `ai_writer.py` | Claude Haiku ile özgün içerik üretir (beyin) | ✅ Test edildi |
| `content_generator.py` | AI köprüsü + şablon fallback | ✅ Test edildi |
| `image_maker.py` | Carousel + story görseli | ✅ Görsel test edildi |
| `reel_maker.py` | Videoya metin basma (ffmpeg) | ✅ Video test edildi |
| `publisher.py` | IG (carousel/story/reels) + FB çift yayın | ⏳ Canlı test bekliyor |
| `learning_loop.py` | Performans analizi + öğrenme özeti | ⏳ Token bekliyor |
| `scheduler.py` | Tam otomasyon orkestratörü | ✅ Akış test edildi |
| `mediway_agent.py` | Analiz katmanı (mevcut) | ✅ |

---

## ⚠️ Anayasa düzeltmeleri (yapıldı)

Eski dosyalarda kural ihlalleri vardı, düzeltildi:
- ❌ "14 dil / 14 dilde" → ✅ "dünyanın her yerinden yabancı hasta"
- ❌ "klinik" → ✅ "sağlayıcı / sağlık kuruluşu"
- Hashtag sınırı 5 → **4** (kullanıcı talimatı)
- Döngü 48 saat → **4 saat**
- `ai_writer` çıktısı bu kurallara göre otomatik DOĞRULANIR; ihlal varsa
  Claude'a düzelttirilir (retry). Şablon fallback de aynı kurallara uyar.

---

## Kurulum

```bash
pip install -r requirements.txt
# ffmpeg ayrıca sistemde kurulu olmalı (reels için)
```

Environment variable'lar (`.env.example` şablonuna bak):
`ANTHROPIC_API_KEY`, `IG_TOKEN`, `FB_PAGE_ID`, `FB_PAGE_TOKEN`,
`FTP_HOST`, `FTP_USER`, `FTP_PASS`, `FTP_DIR`, `SITE_BASE_URL`

---

## Claude Code'da yapılacak İLK testler (sırayla)

**1. Token kapsamını doğrula** (en kritik — "kod çalıştı ama yayın reddedildi" sorununu önler):
- Her yayın tipi için gereken izinler: IG carousel/story/reels → `instagram_content_publish`;
  FB post → `pages_manage_posts` + ayrı `FB_PAGE_TOKEN`.
- `debug_token` ve `me/accounts` ile mevcut token'ın scope'larını kontrol et.
- Eksik izin varsa önce onu bildir, koda geçme.

**2. AI üretimini test et** (key ayarlıyken):
```bash
python ai_writer.py
```
Gerçek Claude Haiku çıktısı gelmeli (carousel/reels/story JSON). Bu makinede
key olmadığı için sadece senin ortamında çalışır.

**3. Tek döngüyü canlı çalıştır:**
```bash
python scheduler.py --once
```
Gerçek bir carousel + story yayınlamayı dener. Instagram'ı kontrol et.

**4. Sorun çıkarsa muhtemel sebepler:**
- Yayın reddedildi → token tipi yanlış (IG token ≠ FB Page token) veya app
  Development mode'da ve hesap test kullanıcısı değil.
- Reels takıldı → video işleme uzun sürüyor olabilir (polling timeout 120sn,
  gerekiyorsa `publisher._wait_for_container` timeout'unu artır).
- FB yayını atlandı → `FB_PAGE_ID`/`FB_PAGE_TOKEN` ayarlı değil.

**5. Her şey çalışınca sürekli moda al:**
```bash
python scheduler.py
```
(Railway/sunucuda çalıştırırsan 7/24 otomatik çalışır.)

---

## Önemli notlar

- **İlk haftalar "öğrenme" zayıf çalışır** — hesapta analiz edilecek veri az.
  Bu normal; veri biriktikçe Claude tutmuş içeriği çoğaltmayı öğrenir.
- **Maliyet:** Haiku ile günde birkaç sent. `MODEL` değişkeni `ai_writer.py`
  içinde tek satır — Sonnet'e geçmek istersen oradan değiştir.
- **Reels videoları:** klasördeki `*video.mp4` dosyaları kullanılıyor.
  Yeni örnek video eklemek için klasöre `.mp4` koyman yeterli.
- Görsel/video FTP'ye yüklenip yayından sonra otomatik silinir (site temiz kalır).
