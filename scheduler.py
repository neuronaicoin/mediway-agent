"""
================================================================
 MEDIWAY AGENT — SCHEDULER (TAM OTOMASYON ORKESTRATÖRÜ)
 (scheduler.py)
================================================================

Agent'ın kalbi. Her 4 SAATTE bir uyanır ve şunu yapar:

  1. Gün değiştiyse günlük sayaçları sıfırla
  2. Performansı analiz et → öğrenme özeti çıkar (learning_loop)
  3. Günlük limit dolmadıysa: içerik üret (AI) → görsel/video yap →
     Instagram'a yayınla → AYNI içeriği Facebook'a yayınla
  4. Limit dolduysa: sadece analiz yap, yayın yapma (spam koruması)
  5. Durumu kaydet, 4 saat uyu, tekrar

GÜNLÜK LİMİT (anayasa): 4 paylaşım (2 carousel + 2 reels) + 5 story.
Her 4 saatte 1 paylaşım + 1 story atar → günde ~4-6 döngü, limitte durur.

----------------------------------------------------------------
ÇALIŞTIRMA:
  python scheduler.py            → sürekli çalışır (Ctrl+C ile durur)
  python scheduler.py --once     → tek döngü çalışır (test için)
----------------------------------------------------------------
"""

import os
import sys
import time
import random
import glob
from datetime import datetime

from content_constitution import CONSTITUTION
from content_generator import generate_post
import image_maker
import reel_maker
import publisher
import learning_loop
import mediway_agent

# Anayasadan limitler
PLAN = CONSTITUTION["publishing_plan"]
MAX_POSTS = PLAN["posts_per_day"]            # 4
MAX_STORIES = PLAN["stories_per_day"]        # 5
CAROUSELS_PER_DAY = PLAN["breakdown"]["carousel"]  # 2
REELS_PER_DAY = PLAN["breakdown"]["reels"]   # 2
INTERVAL_HOURS = PLAN["check_interval_hours"]  # 4
CROSS_FB = PLAN["cross_post_facebook"]       # True

# Örnek videolar (Reels için) — klasördeki .mp4'ler
# Reels artık sıfırdan animasyonla üretiliyor — örnek video gerekmez


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ----------------------------------------------------------------
# TEK PAYLAŞIM: carousel veya reels üret + yayınla (IG + FB)
# ----------------------------------------------------------------
def do_one_post(state, perf_summary):
    """Günün hangi paylaşımı eksikse onu üretip yayınlar."""
    carousels_done = state.get("carousels_today", 0)
    reels_done = state.get("reels_today", 0)

    # Hangi formatı üreteceğine karar ver (eksik olanı tamamla)
    if carousels_done < CAROUSELS_PER_DAY:
        post_type = "carousel"
    elif reels_done < REELS_PER_DAY:
        post_type = "reels"
    else:
        log("  Günlük paylaşım limiti dolu.")
        return False

    log(f"  İçerik üretiliyor: {post_type} ...")
    content = generate_post(post_type, perf_summary)
    caption = content.get("caption", "")

    if post_type == "carousel":
        # Slaytları görsele bas
        files = image_maker.make_carousel(content["slides"], prefix=f"car_{int(time.time())}")
        log(f"  {len(files)} slayt görseli üretildi.")
        ig_id = publisher.publish_carousel(files, caption)
        if CROSS_FB and ig_id:
            # FB'ye ilk slaytı foto olarak + caption
            publisher.publish_to_facebook(caption, image_path=files[0])
        if ig_id:
            state["carousels_today"] = carousels_done + 1
            state["published_today"] = state.get("published_today", 0) + 1
        # Yerel görselleri temizle
        for f in files:
            try: os.remove(f)
            except: pass
        return bool(ig_id)

    else:  # reels
        screen_text = content.get("screen_text", "")
        subtitle = "Sağlık Turizmi"
        out_video = f"reel_{int(time.time())}.mp4"
        os.makedirs("output_videos", exist_ok=True)
        out_path = os.path.join("output_videos", out_video)
        reel_maker.make_reel(screen_text, out_path, subtitle=subtitle)
        log(f"  Animasyonlu reel üretildi: {out_path}")
        ig_id = publisher.publish_reel(out_path, caption)
        if CROSS_FB and ig_id:
            publisher.publish_to_facebook(caption, video_path=out_path)
        if ig_id:
            state["reels_today"] = reels_done + 1
            state["published_today"] = state.get("published_today", 0) + 1
        try: os.remove(out_path)
        except: pass
        return bool(ig_id)


# ----------------------------------------------------------------
# TEK STORY üret + yayınla
# ----------------------------------------------------------------
def do_one_story(state, perf_summary):
    stories_done = state.get("stories_today", 0)
    if stories_done >= MAX_STORIES:
        return False
    log("  Story üretiliyor ...")
    content = generate_post("story", perf_summary)
    text = content.get("screen_text", "")
    img = image_maker.make_story(text, prefix=f"story_{int(time.time())}")
    ig_id = publisher.publish_story(img)
    if ig_id:
        state["stories_today"] = stories_done + 1
    try: os.remove(img)
    except: pass
    return bool(ig_id)


# ----------------------------------------------------------------
# BİR DÖNGÜ
# ----------------------------------------------------------------
def run_cycle():
    log("=" * 55)
    log(" YENİ DÖNGÜ BAŞLADI")
    log("=" * 55)

    state = learning_loop.load_state()
    state = learning_loop.reset_daily_if_needed(state)
    # Format sayaçları (gün sıfırlamasında sıfırlanır)
    if state.get("last_cycle_date") != state["last_date"]:
        state["carousels_today"] = 0
        state["reels_today"] = 0
        state["last_cycle_date"] = state["last_date"]

    log(f" Bugün: {state['published_today']}/{MAX_POSTS} paylaşım, "
        f"{state.get('stories_today',0)}/{MAX_STORIES} story")

    # 1) Öğrenme: performans özeti çıkar
    log(" Performans analiz ediliyor ...")
    try:
        perf_summary = learning_loop.build_performance_summary()
        if perf_summary:
            log(" Öğrenme özeti hazır (AI'a beslenecek).")
    except Exception as e:
        log(f" ⚠️  Analiz hatası: {e}")
        perf_summary = ""

    # 2) Limit kontrolü + yayın
    if state.get("published_today", 0) < MAX_POSTS:
        # OPTIMAL SAAT KONTROLÜ (Aşama 3): kötü saatte ve vakit varsa ertele
        should_post = True
        try:
            best_hours = mediway_agent.get_best_hours(top_n=8)
            current_hour = datetime.now().hour
            remaining_posts = MAX_POSTS - state.get("published_today", 0)
            remaining_cycles = max(1, (24 - current_hour) // INTERVAL_HOURS)
            if best_hours and current_hour not in best_hours:
                if remaining_cycles > remaining_posts:
                    should_post = False
                    log(f" ⏰ Şu an ({current_hour}:00) kitle az aktif. "
                        f"Aktif saatler: {best_hours}. Paylaşım ertelendi.")
        except Exception as e:
            log(f" ⏰ Saat kontrolü atlandı: {e}")
            should_post = True

        if should_post:
            try:
                do_one_post(state, perf_summary)
            except Exception as e:
                log(f" ⚠️  Paylaşım hatası: {e}")
    else:
        log(" Paylaşım limiti dolu — bu döngüde sadece story/analiz.")

    # 3) Story (her döngüde 1, limite kadar)
    if state.get("stories_today", 0) < MAX_STORIES:
        try:
            do_one_story(state, perf_summary)
        except Exception as e:
            log(f" ⚠️  Story hatası: {e}")

    learning_loop.save_state(state)
    log(" Döngü tamamlandı. Durum kaydedildi.")
    return state


# ----------------------------------------------------------------
# ANA DÖNGÜ (sürekli)
# ----------------------------------------------------------------
def main():
    once = "--once" in sys.argv
    log("MEDIWAY AGENT — TAM OTOMASYON BAŞLADI")
    log(f"Döngü aralığı: {INTERVAL_HOURS} saat | "
        f"Günlük: {MAX_POSTS} paylaşım + {MAX_STORIES} story | "
        f"Facebook çift yayın: {CROSS_FB}")

    if once:
        run_cycle()
        log("Tek döngü tamamlandı (--once).")
        return

    while True:
        try:
            run_cycle()
        except KeyboardInterrupt:
            log("Durduruldu (Ctrl+C).")
            break
        except Exception as e:
            log(f"⚠️  Beklenmeyen hata: {e}")
        log(f"💤 {INTERVAL_HOURS} saat uyunuyor ...\n")
        time.sleep(INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    main()
