# MediWay Agent — Railway Kurulum Rehberi (Sade)

Bu agent Railway'de 7/24 otomatik çalışacak. Bilgisayarın kapansa bile durmaz.
Adımlar sırayla — acele etme, her adımı bitirince diğerine geç.

---

## ADIM 1 — GitHub'a repo aç ve dosyaları yükle

1. github.com → giriş yap → sağ üst **+** → **New repository**
2. İsim: `mediway-agent` → **Private** seç (kodun gizli kalsın) → **Create**
3. Açılan sayfada **"uploading an existing file"** linkine tıkla
4. Bu klasördeki TÜM dosyaları sürükle-bırak:
   - Tüm `.py` dosyaları (9 adet)
   - `requirements.txt`, `nixpacks.toml`, `Procfile`, `.gitignore`
   - `1video.mp4`, `2video.mp4`, `3video.mp4`, `4video.mp4` (Reels için şart)
   - `HANDOVER.md`, `RAILWAY_KURULUM.md`
   - ⚠️ `.env` dosyası VARSA YÜKLEME (token'lar açığa çıkar)
5. **Commit changes** bas

---

## ADIM 2 — Railway'e bağla

1. railway.app → giriş yap (GitHub ile giriş yapabilirsin)
2. **New Project** → **Deploy from GitHub repo**
3. `mediway-agent` reposunu seç
4. Railway otomatik olarak `nixpacks.toml`'u okur → ffmpeg + fontları kurar →
   `python scheduler.py` ile başlatır.
5. İlk deploy birkaç dakika sürer (ffmpeg kuruluyor).

---

## ADIM 3 — Environment Variable'ları gir (EN ÖNEMLİ ADIM)

Railway projesinde → **Variables** sekmesi → her birini tek tek ekle
(**New Variable** → isim + değer):

| Variable | Değer |
|----------|-------|
| `ANTHROPIC_API_KEY` | sk-ant-... (Claude API key'in) |
| `IG_TOKEN` | Instagram Page access token |
| `FB_PAGE_ID` | Facebook sayfa ID'n |
| `FB_PAGE_TOKEN` | Facebook Page access token |
| `FTP_HOST` | ftp.mediwayturkey.com |
| `FTP_USER` | FTP kullanıcı adın |
| `FTP_PASS` | FTP şifren |
| `FTP_DIR` | ig-temp |
| `SITE_BASE_URL` | https://mediwayturkey.com/ig-temp |

Variable'ları kaydedince Railway otomatik yeniden başlar.

---

## ADIM 4 — Çalışıyor mu kontrol et

1. Railway → **Deployments** → **View Logs**
2. Loglarda şunları görmelisin:
   - `MEDIWAY AGENT — TAM OTOMASYON BAŞLADI`
   - `YENİ DÖNGÜ BAŞLADI`
   - `İçerik üretiliyor: carousel ...`
   - `4 slayt görseli üretildi`
   - `Carousel yayınlandı! Post ID: ...`  ← bunu görürsen ÇALIŞIYOR 🎉
3. Instagram ve Facebook hesabını kontrol et — paylaşım çıkmış olmalı.

---

## SORUN GİDERME

**"Eksik ayar: IG_TOKEN..."** → Variable'ları girmemişsin/yanlış. Adım 3'e dön.

**"Container hatası / yayın reddedildi"** → Token tipi yanlış olabilir:
- IG yayını için `instagram_content_publish` izinli token gerekir
- FB yayını için AYRI `FB_PAGE_TOKEN` (`pages_manage_posts` izinli) gerekir
- App "Development mode"daysa yayın hesabının app'e admin/test olması gerekir

**Reels takılıyor** → Video işleme uzun sürebilir. Log'da "Video işleniyor"
yazısından sonra bekle; 120 saniyede bitmezse `publisher._wait_for_container`
timeout'unu artır.

**FTP hatası** → FTP bilgilerini ve `SITE_BASE_URL`'in doğru gizli klasörü
gösterdiğini kontrol et. Sitende `ig-temp` klasörü olmalı.

---

## ÖNEMLİ NOTLAR

- **Maliyet:** Railway'in küçük bir aylık ücreti var (~5$) + Claude Haiku
  kullanımı (günde birkaç sent). Çok düşük.
- **İlk haftalar:** Agent "öğrenmek" için veri biriktirir. İçerik kalitesi
  zamanla artar. Bu normal.
- **Yeni örnek video eklemek:** GitHub repoya yeni `.mp4` yükle, Railway
  otomatik çeker.
- **Durdurmak istersen:** Railway'de projeyi pause/delete edebilirsin.
