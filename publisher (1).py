"""
================================================================
 MEDIWAY AGENT — YAYINLAMA MODÜLÜ (TAM — SUPABASE)
 (publisher.py)
================================================================

AKIŞ: Görsel/videoyu Supabase Storage'a yükle → public URL'i Meta'ya
ver → yayınla → dosyayı Storage'dan sil (temiz kalsın).

(FTP yerine Supabase kullanılıyor çünkü site Railway'de, FTP yok.)

DESTEKLENEN YAYIN TİPLERİ:
  • Instagram tek görsel      (publish_single_image)
  • Instagram CAROUSEL         (publish_carousel)        ← 4 slayt birden
  • Instagram STORY            (publish_story)
  • Instagram REELS            (publish_reel)             ← video + polling
  • Facebook çift yayın        (publish_to_facebook)      ← aynı içerik FB'ye

----------------------------------------------------------------
ENVIRONMENT VARIABLE'LAR (hiçbiri koda yazılmaz):
  IG_TOKEN              → Instagram yayını için (Page token)
  FB_PAGE_ID            → Facebook sayfa ID'si
  FB_PAGE_TOKEN         → Facebook sayfa yayını için (ayrı olabilir)
  SUPABASE_URL          → https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY  → Supabase service_role key (gizli)
  SUPABASE_BUCKET       → bucket adı (varsayılan: ig-temp)
----------------------------------------------------------------

Gerektirir:  pip install requests
================================================================
"""

import os
import time
import uuid
import requests

# ----------------------------------------------------------------
# AYARLAR
# ----------------------------------------------------------------
IG_USER_ID   = "17841414815930110"
ACCESS_TOKEN = os.environ.get("IG_TOKEN")

FB_PAGE_ID    = os.environ.get("FB_PAGE_ID")
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN")

# Supabase Storage ayarları
SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "ig-temp")

API_VERSION = "v25.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


# ================================================================
# SUPABASE STORAGE YARDIMCILARI
# ================================================================
def upload_to_site(local_path):
    """Dosyayı Supabase Storage'a yükler, public URL ve dosya adını döner."""
    ext = os.path.splitext(local_path)[1]
    # Çakışmayı önlemek için benzersiz isim
    filename = f"{uuid.uuid4().hex}{ext}"
    print(f"  📤 Supabase'e yükleniyor: {filename} ...")

    # İçerik tipini belirle
    content_type = "video/mp4" if ext.lower() == ".mp4" else "image/png"

    with open(local_path, "rb") as f:
        data = f.read()

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
    r = requests.post(
        upload_url,
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "apikey": SUPABASE_SERVICE_KEY,
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        data=data,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Supabase yükleme hatası ({r.status_code}): {r.text[:300]}")

    # Public URL (bucket public olmalı)
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
    print(f"  ✅ Yüklendi: {public_url}")
    return public_url, filename


def delete_from_site(filename):
    """Yayınlanan dosyayı Supabase Storage'dan siler."""
    try:
        del_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
        requests.delete(
            del_url,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "apikey": SUPABASE_SERVICE_KEY,
            },
        )
        print(f"  🧹 Silindi: {filename}")
    except Exception as e:
        print(f"  ⚠️  Silme hatası (önemsiz): {e}")


def _check_settings(extra=None):
    """Gerekli env değişkenleri ayarlı mı?"""
    missing = []
    if not ACCESS_TOKEN: missing.append("IG_TOKEN")
    if not SUPABASE_URL: missing.append("SUPABASE_URL")
    if not SUPABASE_SERVICE_KEY: missing.append("SUPABASE_SERVICE_KEY")
    for e in (extra or []):
        if not globals().get(e) and not os.environ.get(e):
            missing.append(e)
    return missing


# ================================================================
# STATUS POLLING (Reels/video için — işlenmesini bekle)
# ================================================================
def _wait_for_container(creation_id, timeout=120, interval=5):
    """
    Video/Reels container'ı 'FINISHED' olana kadar bekler.
    IG, videoyu sunucu tarafında işler; hemen publish edilemez.
    """
    print("  ⏳ Video işleniyor (status bekleniyor) ...")
    waited = 0
    while waited < timeout:
        r = requests.get(
            f"{BASE_URL}/{creation_id}",
            params={"fields": "status_code", "access_token": ACCESS_TOKEN},
        ).json()
        status = r.get("status_code")
        if status == "FINISHED":
            print("  ✅ Video hazır.")
            return True
        if status == "ERROR":
            print(f"  ❌ Video işleme hatası: {r}")
            return False
        time.sleep(interval)
        waited += interval
    print("  ⚠️  Zaman aşımı — video işlenemedi.")
    return False


# ================================================================
# 1) INSTAGRAM TEK GÖRSEL
# ================================================================
def publish_single_image(image_url, caption):
    create = requests.post(
        f"{BASE_URL}/{IG_USER_ID}/media",
        data={"image_url": image_url, "caption": caption, "access_token": ACCESS_TOKEN},
    ).json()
    if "error" in create:
        print(f"  ❌ Container hatası: {create['error'].get('message')}")
        return None
    creation_id = create.get("id")
    time.sleep(5)
    publish = requests.post(
        f"{BASE_URL}/{IG_USER_ID}/media_publish",
        data={"creation_id": creation_id, "access_token": ACCESS_TOKEN},
    ).json()
    if "error" in publish:
        print(f"  ❌ Yayın hatası: {publish['error'].get('message')}")
        return None
    print(f"  🎉 Yayınlandı! Post ID: {publish.get('id')}")
    return publish.get("id")


# ================================================================
# 2) INSTAGRAM CAROUSEL (çoklu slayt)
# ================================================================
def publish_carousel(image_paths, caption):
    """
    Birden fazla görseli tek carousel olarak yayınlar.
    Her slayt: yükle → child container (is_carousel_item).
    Sonra: parent carousel container → publish. En son hepsini sil.
    """
    print("\n" + "=" * 50)
    print(f" INSTAGRAM CAROUSEL ({len(image_paths)} slayt)")
    print("=" * 50)

    missing = _check_settings()
    if missing:
        print(f"❌ Eksik ayar: {', '.join(missing)}")
        return None

    child_ids = []
    uploaded = []
    try:
        # 1) Her slaytı yükle + child container oluştur
        for path in image_paths:
            url, fname = upload_to_site(path)
            uploaded.append(fname)
            r = requests.post(
                f"{BASE_URL}/{IG_USER_ID}/media",
                data={
                    "image_url": url,
                    "is_carousel_item": "true",
                    "access_token": ACCESS_TOKEN,
                },
            ).json()
            if "error" in r:
                print(f"  ❌ Child container hatası: {r['error'].get('message')}")
                return None
            child_ids.append(r["id"])
            print(f"  ✅ Slayt container: {r['id']}")
            time.sleep(2)

        # 2) Parent carousel container
        parent = requests.post(
            f"{BASE_URL}/{IG_USER_ID}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": ACCESS_TOKEN,
            },
        ).json()
        if "error" in parent:
            print(f"  ❌ Carousel container hatası: {parent['error'].get('message')}")
            return None
        time.sleep(5)

        # 3) Yayınla
        publish = requests.post(
            f"{BASE_URL}/{IG_USER_ID}/media_publish",
            data={"creation_id": parent["id"], "access_token": ACCESS_TOKEN},
        ).json()
        if "error" in publish:
            print(f"  ❌ Yayın hatası: {publish['error'].get('message')}")
            return None
        print(f"  🎉 Carousel yayınlandı! Post ID: {publish.get('id')}")
        return publish.get("id")
    finally:
        # Sunucuyu temizle
        time.sleep(2)
        for fname in uploaded:
            delete_from_site(fname)


# ================================================================
# 3) INSTAGRAM STORY
# ================================================================
def publish_story(image_path):
    print("\n" + "=" * 50)
    print(" INSTAGRAM STORY")
    print("=" * 50)
    missing = _check_settings()
    if missing:
        print(f"❌ Eksik ayar: {', '.join(missing)}")
        return None

    url, fname = upload_to_site(image_path)
    try:
        create = requests.post(
            f"{BASE_URL}/{IG_USER_ID}/media",
            data={"image_url": url, "media_type": "STORIES", "access_token": ACCESS_TOKEN},
        ).json()
        if "error" in create:
            print(f"  ❌ Story container hatası: {create['error'].get('message')}")
            return None
        time.sleep(5)
        publish = requests.post(
            f"{BASE_URL}/{IG_USER_ID}/media_publish",
            data={"creation_id": create["id"], "access_token": ACCESS_TOKEN},
        ).json()
        if "error" in publish:
            print(f"  ❌ Story yayın hatası: {publish['error'].get('message')}")
            return None
        print(f"  🎉 Story yayınlandı! ID: {publish.get('id')}")
        return publish.get("id")
    finally:
        time.sleep(2)
        delete_from_site(fname)


# ================================================================
# 4) INSTAGRAM REELS (video + polling)
# ================================================================
def publish_reel(video_path, caption):
    print("\n" + "=" * 50)
    print(" INSTAGRAM REELS")
    print("=" * 50)
    missing = _check_settings()
    if missing:
        print(f"❌ Eksik ayar: {', '.join(missing)}")
        return None

    url, fname = upload_to_site(video_path)
    try:
        create = requests.post(
            f"{BASE_URL}/{IG_USER_ID}/media",
            data={
                "media_type": "REELS",
                "video_url": url,
                "caption": caption,
                "access_token": ACCESS_TOKEN,
            },
        ).json()
        if "error" in create:
            print(f"  ❌ Reels container hatası: {create['error'].get('message')}")
            return None

        # Video işlenmesini bekle (kritik — yoksa publish başarısız olur)
        if not _wait_for_container(create["id"]):
            return None

        publish = requests.post(
            f"{BASE_URL}/{IG_USER_ID}/media_publish",
            data={"creation_id": create["id"], "access_token": ACCESS_TOKEN},
        ).json()
        if "error" in publish:
            print(f"  ❌ Reels yayın hatası: {publish['error'].get('message')}")
            return None
        print(f"  🎉 Reels yayınlandı! ID: {publish.get('id')}")
        return publish.get("id")
    finally:
        time.sleep(2)
        delete_from_site(fname)


# ================================================================
# 5) FACEBOOK ÇİFT YAYIN
# ================================================================
def publish_to_facebook(caption, image_path=None, video_path=None):
    """
    Aynı içeriği Facebook sayfasına yayınlar.
    - image_path verilirse: foto gönderisi (/photos)
    - video_path verilirse: video gönderisi (/videos)
    - hiçbiri yoksa: sadece metin (/feed)
    FB_PAGE_ID + FB_PAGE_TOKEN gerektirir.
    """
    print("\n" + "=" * 50)
    print(" FACEBOOK ÇİFT YAYIN")
    print("=" * 50)
    if not FB_PAGE_ID or not FB_PAGE_TOKEN:
        print("  ⚠️  FB_PAGE_ID / FB_PAGE_TOKEN ayarlı değil — FB yayını atlandı.")
        return None
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("  ❌ Supabase ayarları eksik.")
        return None

    uploaded = None
    try:
        if image_path:
            url, uploaded = upload_to_site(image_path)
            r = requests.post(
                f"{BASE_URL}/{FB_PAGE_ID}/photos",
                data={"url": url, "caption": caption, "access_token": FB_PAGE_TOKEN},
            ).json()
        elif video_path:
            url, uploaded = upload_to_site(video_path)
            r = requests.post(
                f"{BASE_URL}/{FB_PAGE_ID}/videos",
                data={"file_url": url, "description": caption, "access_token": FB_PAGE_TOKEN},
            ).json()
        else:
            r = requests.post(
                f"{BASE_URL}/{FB_PAGE_ID}/feed",
                data={"message": caption, "access_token": FB_PAGE_TOKEN},
            ).json()

        if "error" in r:
            print(f"  ❌ FB yayın hatası: {r['error'].get('message')}")
            return None
        post_id = r.get("id") or r.get("post_id")
        print(f"  🎉 Facebook'ta yayınlandı! ID: {post_id}")
        return post_id
    finally:
        if uploaded:
            time.sleep(2)
            delete_from_site(uploaded)


# ================================================================
# YÜKSEK SEVİYE: tek görseli baştan sona yayınla (geri uyumluluk)
# ================================================================
def publish_image_post(local_image_path, caption):
    print("\n" + "=" * 50)
    print(" TEK GÖRSEL YAYINLAMA")
    print("=" * 50)
    missing = _check_settings()
    if missing:
        print(f"❌ Eksik ayar: {', '.join(missing)}")
        return None
    url, filename = upload_to_site(local_image_path)
    post_id = publish_single_image(url, caption)
    time.sleep(2)
    delete_from_site(filename)
    return post_id


# ----------------------------------------------------------------
# TEST (gerçek yayın YAPMAZ — sadece ayar kontrolü)
# ----------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print(" PUBLISHER — ayar kontrolü")
    print("=" * 50)
    missing = _check_settings()
    if missing:
        print(f"\n⚠️  Eksik env: {', '.join(missing)}")
    else:
        print("\n✅ Instagram ayarları tam.")
    if FB_PAGE_ID and FB_PAGE_TOKEN:
        print("✅ Facebook ayarları tam.")
    else:
        print("⚠️  Facebook ayarları eksik (FB_PAGE_ID / FB_PAGE_TOKEN).")
    print("\nGerçek yayın testi Claude Code'da, env'ler ayarlıyken yapılır.")