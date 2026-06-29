"""
================================================================
 MEDIWAY INSTAGRAM AGENT — Başlangıç İskeleti (Aşama 1)
 Bağlantı + Analiz Katmanı
================================================================

Bu dosya, bugün Graph API Explorer'da elle test ettiğin sorguların
kodlanmış halidir. Yani burada YENİ bir şey yok — sadece çalıştığını
gördüğün şeyleri Python'a taşıdık.

Bu aşamada agent ŞUNLARI yapar:
  1. Token'ı güvenli (environment variable) okur
  2. Instagram hesabının temel bilgilerini çeker (takipçi, gönderi sayısı)
  3. Geçmiş gönderileri ve performanslarını (beğeni/yorum) çeker
  4. Basit bir performans analizi yapar (hangi gönderi tuttu)

Henüz YAPMAZ (sonraki aşamalar):
  - İçerik üretmek
  - Paylaşım yapmak
  - Story atmak
Önce "okuma ve analiz" sağlam çalışsın, sonra "yazma" eklenir.

----------------------------------------------------------------
KURULUM (bir kez):
  1. Python yüklü olmalı (python.org)
  2. Terminal/komut satırında:  pip install requests
  3. Token'ı environment variable olarak ayarla (AŞAĞIDA anlatıldı)
  4. Çalıştır:  python mediway_agent.py
----------------------------------------------------------------

TOKEN'I GÜVENLİ AYARLAMA (token'ı koda YAZMA!):
  Windows (komut satırı):
      setx IG_TOKEN "buraya_kalici_page_token"
      (sonra terminali kapatıp yeniden aç)
  Mac/Linux:
      export IG_TOKEN="buraya_kalici_page_token"
      (kalıcı olması için ~/.bashrc veya ~/.zshrc içine ekle)

  Bu sayede token kodun içinde görünmez, kazara paylaşılmaz.
================================================================
"""

import os
import requests
from datetime import datetime

# ----------------------------------------------------------------
# AYARLAR
# ----------------------------------------------------------------

# Instagram Business Account ID — bugün bunu bulduk, gizli değil.
IG_USER_ID = os.environ.get("IG_USER_ID", "17841414815930110")

# Token environment variable'dan okunur (koda asla yazma!)
ACCESS_TOKEN = os.environ.get("IG_TOKEN")

# Graph API sürümü
API_VERSION = "v25.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


# ----------------------------------------------------------------
# YARDIMCI: Güvenli API çağrısı
# ----------------------------------------------------------------
def api_get(path, params=None):
    """Graph API'ye GET isteği atar, sonucu sözlük olarak döner."""
    if params is None:
        params = {}
    params["access_token"] = ACCESS_TOKEN
    url = f"{BASE_URL}/{path}"
    response = requests.get(url, params=params)
    data = response.json()

    # Hata kontrolü
    if "error" in data:
        err = data["error"]
        print(f"  ⚠️  API HATASI: {err.get('message')}")
        print(f"      (kod: {err.get('code')})")
        return None
    return data


# ----------------------------------------------------------------
# 1) HESAP BİLGİLERİNİ ÇEK
# ----------------------------------------------------------------
def get_account_info():
    """Hesabın temel bilgilerini çeker (test ettiğin sorgunun aynısı)."""
    print("\n📊 HESAP BİLGİLERİ")
    print("-" * 50)
    data = api_get(
        IG_USER_ID,
        {"fields": "username,name,followers_count,media_count,biography"}
    )
    if not data:
        return None

    print(f"  Kullanıcı adı : @{data.get('username')}")
    print(f"  İsim          : {data.get('name')}")
    print(f"  Takipçi       : {data.get('followers_count')}")
    print(f"  Gönderi sayısı: {data.get('media_count')}")
    return data


# ----------------------------------------------------------------
# 2) GEÇMİŞ GÖNDERİLERİ ÇEK
# ----------------------------------------------------------------
def get_best_hours(top_n=6):
    """
    Takipçilerin en aktif olduğu saatleri döner (0-23 arası saat listesi).
    Instagram 'online_followers' insight'ından hesaplar.
    Veri yoksa boş liste döner (agent normal saatte yayınlar).
    Not: Hesabın az takipçisi varsa Instagram bu veriyi vermez — normal.
    """
    try:
        data = api_get(f"{IG_USER_ID}/insights", {
            "metric": "online_followers",
            "period": "lifetime",
        })
        if not data or "data" not in data or not data["data"]:
            return []
        values = data["data"][0].get("values", [])
        if not values:
            return []
        # Son günün saat-bazlı aktiflik haritası: {saat: takipçi_sayısı}
        hourly = values[-1].get("value", {})
        if not hourly:
            return []
        # En aktif top_n saati seç
        sorted_hours = sorted(hourly.items(), key=lambda kv: -kv[1])
        best = [int(h) for h, _ in sorted_hours[:top_n]]
        return sorted(best)
    except Exception:
        return []


def get_media_insights(media_id, media_type):
    """
    Bir gönderinin GERÇEK performans verisini çeker (Insights API).
    reach (erişim), saved (kaydetme), shares (paylaşma), views.
    Kaydetme ve paylaşma, algoritma için beğeniden çok daha değerlidir.
    """
    # Medya tipine göre uygun metrikler (Reels farklı metrik ister)
    if media_type == "VIDEO":
        metrics = "reach,saved,shares,likes,comments,views"
    else:
        metrics = "reach,saved,shares,likes,comments"
    data = api_get(f"{media_id}/insights", {"metric": metrics})
    out = {}
    if data and "data" in data:
        for m in data["data"]:
            name = m.get("name")
            vals = m.get("values", [{}])
            out[name] = vals[0].get("value", 0) if vals else 0
    return out


def get_recent_media(limit=25):
    """Son gönderileri ve GERÇEK performanslarını (insights) çeker."""
    print("\n📷 SON GÖNDERİLER")
    print("-" * 50)
    data = api_get(
        f"{IG_USER_ID}/media",
        {
            "fields": "id,caption,media_type,like_count,comments_count,timestamp",
            "limit": limit,
        },
    )
    if not data or "data" not in data:
        return []

    posts = data["data"]
    # Her gönderiye gerçek insights ekle (reach, saved, shares)
    for p in posts:
        try:
            ins = get_media_insights(p["id"], p.get("media_type", ""))
            p["reach"] = ins.get("reach", 0)
            p["saved"] = ins.get("saved", 0)
            p["shares"] = ins.get("shares", 0)
            p["views"] = ins.get("views", 0)
        except Exception:
            p["reach"] = p["saved"] = p["shares"] = p["views"] = 0
    print(f"  Toplam {len(posts)} gönderi çekildi (gerçek insights ile).\n")
    return posts


# ----------------------------------------------------------------
# 3) BASİT PERFORMANS ANALİZİ
# ----------------------------------------------------------------
def analyze_performance(posts):
    """
    Gönderileri analiz eder: ortalama etkileşim, en iyi/en kötü gönderi,
    medya tipine göre performans. Agent'ın 'öğrenme' temeli budur.
    """
    print("\n🧠 PERFORMANS ANALİZİ")
    print("=" * 50)

    if not posts:
        print("  Analiz edilecek gönderi yok.")
        return

    # Her gönderiye toplam etkileşim ekle
    for p in posts:
        likes = p.get("like_count", 0) or 0
        comments = p.get("comments_count", 0) or 0
        p["engagement"] = likes + comments

    # Ortalama etkileşim
    total_eng = sum(p["engagement"] for p in posts)
    avg_eng = total_eng / len(posts)
    print(f"  Ortalama etkileşim : {avg_eng:.1f} (beğeni+yorum)")

    # En iyi gönderi
    best = max(posts, key=lambda x: x["engagement"])
    print(f"\n  🏆 EN İYİ GÖNDERİ ({best['engagement']} etkileşim):")
    caption = (best.get("caption") or "")[:80]
    print(f"     \"{caption}...\"")
    print(f"     Tip: {best.get('media_type')} | Tarih: {best.get('timestamp', '')[:10]}")

    # Medya tipine göre ortalama
    print(f"\n  📈 MEDYA TİPİNE GÖRE:")
    types = {}
    for p in posts:
        t = p.get("media_type", "BİLİNMEYEN")
        types.setdefault(t, []).append(p["engagement"])
    for t, vals in types.items():
        print(f"     {t:12} → ortalama {sum(vals)/len(vals):.1f} etkileşim ({len(vals)} gönderi)")

    # Basit öğrenme çıkarımı
    print(f"\n  💡 ÇIKARIM:")
    if avg_eng < 1:
        print("     Etkileşim çok düşük. İçerik kitleye ulaşmıyor olabilir —")
        print("     format, paylaşım saati ve hedef kitle gözden geçirilmeli.")
    else:
        best_type = max(types.items(), key=lambda kv: sum(kv[1])/len(kv[1]))[0]
        print(f"     En iyi performans gösteren format: {best_type}")
        print(f"     Bu formattan daha fazla üretilmeli.")


# ----------------------------------------------------------------
# ANA AKIŞ
# ----------------------------------------------------------------
def main():
    print("=" * 50)
    print(" MEDIWAY INSTAGRAM AGENT — Aşama 1: Okuma & Analiz")
    print("=" * 50)

    # Token kontrolü
    if not ACCESS_TOKEN:
        print("\n❌ HATA: IG_TOKEN environment variable bulunamadı.")
        print("   Token'ı ayarla (dosyanın başındaki açıklamaya bak),")
        print("   sonra tekrar çalıştır.")
        return

    # 1. Hesap bilgisi
    account = get_account_info()
    if not account:
        print("\n❌ Hesap bilgisi alınamadı. Token'ı kontrol et.")
        return

    # 2. Gönderileri çek
    posts = get_recent_media(limit=25)

    # 3. Analiz et
    analyze_performance(posts)

    print("\n" + "=" * 50)
    print(" ✅ Aşama 1 tamamlandı. Agent hesabı okuyabiliyor.")
    print(" Sonraki aşama: içerik üretme + yayınlama.")
    print("=" * 50)


if __name__ == "__main__":
    main()
