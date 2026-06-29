"""
================================================================
 MEDIWAY AGENT — ÖĞRENME DÖNGÜSÜ
 (learning_loop.py)
================================================================

Agent'ın "öğrenen" tarafı. Her döngüde:
  1. Son gönderilerin performansını çeker (mediway_agent.analyze)
  2. Ne tuttu / ne tutmadı özetini çıkarır
  3. Bu özeti ai_writer'a besler → Claude bir sonraki içeriği buna
     göre yazar (tutmuş tarzı çoğalt, tutmayanı bırak)

Böylece her gün biraz daha iyi içerik üretilir.
Veri biriktikçe öğrenme keskinleşir (ilk haftalar veri azdır — normal).
================================================================
"""

import os
import json
from datetime import datetime

import mediway_agent  # mevcut analiz katmanı

STATE_FILE = "agent_state.json"


# ----------------------------------------------------------------
# DURUM KAYDI (kalıcı hafıza — döngüler arası)
# ----------------------------------------------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"published_today": 0, "stories_today": 0, "last_date": "",
            "history": [], "best_format": None}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def reset_daily_if_needed(state):
    """Gün değiştiyse günlük sayaçları sıfırla."""
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_date") != today:
        state["published_today"] = 0
        state["stories_today"] = 0
        state["last_date"] = today
    return state


# ----------------------------------------------------------------
# PERFORMANS ÖZETİ — ai_writer'a beslenecek metin
# ----------------------------------------------------------------
def build_performance_summary():
    """
    Son gönderileri analiz edip Claude'un anlayacağı kısa özet döner.
    ai_writer.generate_post(performance_summary=...) ile kullanılır.
    """
    if not os.environ.get("IG_TOKEN"):
        return ""  # token yok — analiz yapılamaz, Claude körlemesine üretir
    posts = mediway_agent.get_recent_media(limit=25)
    if not posts:
        return ""  # veri yok — Claude körlemesine üretir (ilk günler normal)

    for p in posts:
        likes = p.get("like_count", 0) or 0
        comments = p.get("comments_count", 0) or 0
        saved = p.get("saved", 0) or 0
        shares = p.get("shares", 0) or 0
        reach = p.get("reach", 0) or 0
        # AKILLI SKOR: kaydetme ve paylaşma algoritma için en değerli.
        # saved x3, shares x4 (en güçlü sinyal), comments x2, likes x1
        p["engagement"] = likes + comments * 2 + saved * 3 + shares * 4
        p["reach"] = reach
        # Erişime göre oran (küçük hesap büyük hesapla adil karşılaştırılsın)
        p["save_rate"] = (saved / reach) if reach > 0 else 0

    # Medya tipine göre ortalama
    types = {}
    for p in posts:
        t = p.get("media_type", "BİLİNMEYEN")
        types.setdefault(t, []).append(p["engagement"])
    type_avgs = {t: sum(v) / len(v) for t, v in types.items()}

    # En iyi gönderi
    best = max(posts, key=lambda x: x["engagement"])
    best_caption = (best.get("caption") or "")[:120]

    # Özet metni (Claude'a girdi)
    lines = ["Son gönderi performansı (gerçek Instagram verisi):"]
    for t, avg in sorted(type_avgs.items(), key=lambda kv: -kv[1]):
        lines.append(f"- {t}: ortalama {avg:.1f} ağırlıklı skor (kaydetme/paylaşma öncelikli)")

    # Toplam gerçek metrikler
    total_reach = sum(p.get("reach", 0) for p in posts)
    total_saved = sum(p.get("saved", 0) for p in posts)
    total_shares = sum(p.get("shares", 0) for p in posts)
    lines.append(f"Toplam erişim: {total_reach}, kaydetme: {total_saved}, paylaşma: {total_shares}")

    if best["engagement"] > 0:
        lines.append(
            f"EN ÇOK TUTAN gönderi (skor {best['engagement']}, "
            f"{best.get('saved',0)} kaydetme, {best.get('shares',0)} paylaşma) şu tarzdaydı: \"{best_caption}\""
        )
        lines.append("Bu konuyu/tarzı/hook'u ÇOĞALT — kaydedilesi ve paylaşılası içerik üret.")
    else:
        lines.append("Henüz güçlü tutan içerik yok — farklı açılar, daha çarpıcı hook'lar dene.")

    return "\n".join(lines)


# ----------------------------------------------------------------
# EN İYİ FORMAT (plan ağırlığı için)
# ----------------------------------------------------------------
def best_performing_format():
    posts = mediway_agent.get_recent_media(limit=25)
    if not posts:
        return None
    for p in posts:
        likes = p.get("like_count", 0) or 0
        comments = p.get("comments_count", 0) or 0
        saved = p.get("saved", 0) or 0
        shares = p.get("shares", 0) or 0
        p["engagement"] = likes + comments * 2 + saved * 3 + shares * 4
    types = {}
    for p in posts:
        t = p.get("media_type", "")
        types.setdefault(t, []).append(p["engagement"])
    if not types:
        return None
    return max(types.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))[0]


if __name__ == "__main__":
    print("=" * 50)
    print(" ÖĞRENME DÖNGÜSÜ — performans özeti testi")
    print("=" * 50)
    if not os.environ.get("IG_TOKEN"):
        print("\n⚠️  IG_TOKEN yok — gerçek veri çekilemez.")
        print("   Claude Code'da token varken çalışır.")
    else:
        summary = build_performance_summary()
        print("\nÜretilen özet (ai_writer'a beslenecek):\n")
        print(summary or "(veri yok)")
