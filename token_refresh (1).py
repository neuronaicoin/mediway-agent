"""
================================================================
 OTOMATİK TOKEN YENİLEME (token_refresh.py)
================================================================
Amaç: IG_TOKEN'ı her başlangıçta otomatik "uzun ömürlü" hale getirir.
Bir daha elle token yenileme derdi olmaz.

Nasıl çalışır:
  1. Mevcut IG_TOKEN'ı alır
  2. FB_APP_ID + FB_APP_SECRET varsa, token'ı uzun ömürlü User token'a çevirir
  3. Oradan kalıcı Page token alır
  4. Bu yeni token'ı kullanır

Railway'e eklenmesi gereken (token derdini bitirmek için):
  FB_APP_ID      = uygulamanın App ID'si
  FB_APP_SECRET  = uygulamanın App Secret'ı
  FB_PAGE_ID     = Facebook sayfa ID'si (zaten var)

Bunlar yoksa, kod sessizce mevcut IG_TOKEN'ı kullanır (eski davranış).
================================================================
"""

import os
import requests

GRAPH = "https://graph.facebook.com/v21.0"


def _log(msg):
    print(f"[token_refresh] {msg}", flush=True)


def get_long_lived_token():
    """
    Mevcut token'ı uzun ömürlü kalıcı Page token'a çevirmeye çalışır.
    Başarısız olursa mevcut IG_TOKEN'ı döndürür (sistem durmaz).
    """
    current = os.environ.get("IG_TOKEN")
    app_id = os.environ.get("FB_APP_ID")
    app_secret = os.environ.get("FB_APP_SECRET")
    page_id = os.environ.get("FB_PAGE_ID")

    # App bilgileri yoksa mevcut token'la devam et
    if not (app_id and app_secret):
        _log("FB_APP_ID/FB_APP_SECRET yok — mevcut IG_TOKEN kullanılıyor.")
        return current

    if not current:
        _log("IG_TOKEN yok.")
        return current

    try:
        # 1) Mevcut token'ı uzun ömürlü User token'a çevir
        r = requests.get(f"{GRAPH}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": current,
        }, timeout=30)
        data = r.json()

        if "access_token" not in data:
            _log(f"Uzun ömürlü çevirme başarısız: {data.get('error', {}).get('message', data)}")
            return current

        long_user_token = data["access_token"]
        _log("Uzun ömürlü User token alındı.")

        # 2) Page ID varsa, kalıcı Page token al
        if page_id:
            r2 = requests.get(f"{GRAPH}/{page_id}", params={
                "fields": "access_token",
                "access_token": long_user_token,
            }, timeout=30)
            data2 = r2.json()
            if "access_token" in data2:
                _log("Kalıcı Page token alındı ✅")
                return data2["access_token"]
            else:
                _log(f"Page token alınamadı: {data2.get('error', {}).get('message', data2)}")

        # Page token alınamadıysa uzun User token'ı dön
        return long_user_token

    except Exception as e:
        _log(f"Token yenileme hatası: {e} — mevcut token kullanılıyor.")
        return current


# Başlangıçta bir kez çalışır, sonucu publisher kullanır
REFRESHED_TOKEN = get_long_lived_token()
