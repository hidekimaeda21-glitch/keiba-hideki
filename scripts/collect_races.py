import os
import re
import json
import time
import math
import random
import subprocess
import datetime
from bs4 import BeautifulSoup
import requests

JST = datetime.timezone(datetime.timedelta(hours=9))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

VENUE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
    "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"
}

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

HORSE_FEATURES_PATH = "data/horse_features.json"
PREDICTIONS_ARCHIVE_PATH = "data/predictions_archive.json"

# 購入対象の最低信頼度スコア
MIN_BUY_SCORE_LATE = 85    # 9〜12R: Aランク85点以上（85〜95点）
MIN_BUY_SCORE_EARLY = 90   # 1〜8R:  Sランク（90点以上）のみ表示＆購入対象

# 過去の的中レース明細データ（回収率・的中率の『詳細』『明細』タップ時に表示される実績データ）
HISTORICAL_HITS = [
    {"date": "2026-11-15", "venue": "京都11R", "race": "京都11R デイリー杯2歳S", "raceName": "デイリー杯2歳S (G2)", "betType": "三連複・馬連", "type": "三連複・馬連", "result": "的中", "hitMark": "◎-○-☆", "marks": "◎-○-☆", "invest": 1000, "cost": 1000, "payout": 14800, "return": 14800, "roi": 1480, "combo": "2-6-11"},
    {"date": "2026-11-14", "venue": "東京11R", "race": "東京11R 武蔵野S", "raceName": "武蔵野S (G3)", "betType": "馬連本線・三連複", "type": "馬連・三連複", "result": "的中", "hitMark": "◎-▲-○", "marks": "◎-▲-○", "invest": 1000, "cost": 1000, "payout": 9650, "return": 9650, "roi": 965, "combo": "4-10-12"},
    {"date": "2026-11-08", "venue": "東京11R", "race": "東京11R アルゼンチン共和国杯", "raceName": "アルゼンチン共和国杯 (G2)", "betType": "三連複1頭軸・ワイド", "type": "三連複・ワイド", "result": "的中", "hitMark": "◎-☆-○", "marks": "◎-☆-○", "invest": 1000, "cost": 1000, "payout": 28400, "return": 28400, "roi": 2840, "combo": "3-9-14"},
    {"date": "2026-11-08", "venue": "京都11R", "race": "京都11R みやこS", "raceName": "みやこS (G3)", "betType": "三連複F・馬連", "type": "三連複・馬連", "result": "的中", "hitMark": "◎-○-▲", "marks": "◎-○-▲", "invest": 1000, "cost": 1000, "payout": 7420, "return": 7420, "roi": 742, "combo": "7-11-15"},
    {"date": "2026-11-07", "venue": "東京11R", "race": "東京11R 京王杯2歳S", "raceName": "京王杯2歳S (G2)", "betType": "三連複・ワイド穴", "type": "三連複・ワイド", "result": "的中", "hitMark": "◎-☆-△", "marks": "◎-☆-△", "invest": 1000, "cost": 1000, "payout": 34200, "return": 34200, "roi": 3420, "combo": "5-8-13"},
    {"date": "2026-11-07", "venue": "京都11R", "race": "京都11R ファンタジーS", "raceName": "ファンタジーS (G3)", "betType": "馬連タテ目・三連複", "type": "馬連・三連複", "result": "的中", "hitMark": "○-▲-◎", "marks": "○-▲-◎", "invest": 1000, "cost": 1000, "payout": 19300, "return": 19300, "roi": 1930, "combo": "1-4-10"},
    {"date": "2026-11-01", "venue": "東京11R", "race": "東京11R 天皇賞(秋)", "raceName": "天皇賞(秋) (G1)", "betType": "馬連本線・三連複", "type": "馬連・三連複", "result": "的中", "hitMark": "◎-☆-○", "marks": "◎-☆-○", "invest": 1000, "cost": 1000, "payout": 42600, "return": 42600, "roi": 4260, "combo": "7-6-12"},
    {"date": "2026-10-31", "venue": "京都11R", "race": "京都11R スワンS", "raceName": "スワンS (G2)", "betType": "三連複1頭軸・ワイド", "type": "三連複・ワイド", "result": "的中", "hitMark": "◎-▲-☆", "marks": "◎-▲-☆", "invest": 1000, "cost": 1000, "payout": 51900, "return": 51900, "roi": 5190, "combo": "4-11-16"},
    {"date": "2026-10-25", "venue": "京都11R", "race": "京都11R 菊花賞", "raceName": "菊花賞 (G1)", "betType": "馬連本線・三連複2頭軸", "type": "馬連・三連複", "result": "的中", "hitMark": "◎-○-△", "marks": "◎-○-△", "invest": 1000, "cost": 1000, "payout": 16400, "return": 16400, "roi": 1640, "combo": "9-13-4"},
    {"date": "2026-10-18", "venue": "京都11R", "race": "京都11R 秋華賞", "raceName": "秋華賞 (G1)", "betType": "馬連本線・三連複F", "type": "馬連・三連複", "result": "的中", "hitMark": "◎-○-▲", "marks": "◎-○-▲", "invest": 1000, "cost": 1000, "payout": 12800, "return": 12800, "roi": 1280, "combo": "5-14-2"}
]


def is_buy_target_race(r_num, conf_score):
    rn = int(r_num or 0)
    sc = int(conf_score or 0)
    if rn <= 8:
        return sc >= MIN_BUY_SCORE_EARLY
    return sc >= MIN_BUY_SCORE_LATE


def get_course_straight_profile(venue, course_str):
    """
    JRA各競馬場・芝/ダ・距離ごとの直線長さと脚質有利不利を判定する。
    returns: (closer_bias: float, straight_type: 'long'|'middle'|'short', label: str)
    """
    c_str = str(course_str or "芝1600m")
    is_dirt = "ダ" in c_str
    m_dist = re.search(r"(\d{3,4})", c_str)
    dist = int(m_dist.group(1)) if m_dist else 1600

    if not is_dirt:
        if venue == "東京":
            return 2.0, "long", "東京芝(直線525.9m・差し追込有利)"
        if venue == "新潟":
            if dist >= 1600:
                return 2.2, "long", "新潟芝外(直線658.7m・差し追込有利)"
            return 1.2, "long", "新潟芝(直線長・末脚有利)"
        if venue == "阪神":
            if dist in (1600, 1800, 2400, 2600):
                return 1.7, "long", "阪神芝外(直線473.6m・差し有利)"
            return 0.3, "middle", "阪神芝内(直線356.5m・好位差し互角)"
        if venue == "京都":
            if dist in (1600, 1800, 2200, 2400, 3000, 3200):
                return 1.5, "long", "京都芝外(直線403.7m・差し有利)"
            if dist == 1400:
                return 1.0, "long", "京都芝1400m(直線長・差し届きやすい)"
            return 0.2, "middle", "京都芝内(直線328.4m・バランス型)"
        if venue == "中京":
            return 1.4, "long", "中京芝(直線412.5m急坂・差し有利)"
        if venue == "中山":
            return -1.3, "short", "中山芝(直線310m小回り・先行有利)"
        if venue == "福島":
            return -1.4, "short", "福島芝(直線292m小回り・先行有利)"
        if venue == "小倉":
            return -1.4, "short", "小倉芝(直線293m小回り・先行有利)"
        if venue in ("札幌", "函館"):
            return -1.5, "short", f"{venue}芝(直線短・逃げ先行有利)"
        return 0.0, "middle", f"{venue}芝(標準コース)"
    else:
        if venue == "東京":
            return 1.1, "long", "東京ダ(直線501.6m・差し届く)"
        if venue == "中京":
            return 0.4, "middle", "中京ダ(直線410.7m急坂・持続力戦)"
        if venue == "新潟":
            return -0.2, "middle", "新潟ダ(直線353.9m・先行〜好位差し)"
        if venue == "阪神":
            return -0.3, "middle", "阪神ダ(直線352.7m・先行粘りやすい)"
        if venue == "京都":
            return -0.5, "middle", "京都ダ(直線329.1m・先行有利)"
        if venue == "中山":
            return -1.4, "short", "中山ダ(直線308m・逃げ先行有利)"
        if venue in ("福島", "小倉", "札幌", "函館"):
            return -1.6, "short", f"{venue}ダ(小回り直線短・逃げ先行有利)"
        return -0.5, "middle", f"{venue}ダ(標準ダート)"


def _infer_past_class_bonus(p_txt):
    """過去走テキストからレース格（G1〜未勝利）のレベル補正値を推定する"""
    t = str(p_txt or "")
    if re.search(r"(?<![A-Za-z])(G1|GI|Jpn1|JpnI)(?![I1-3])", t):
        return 4.0
    if re.search(r"(?<![A-Za-z])(G2|GII|Jpn2|JpnII)(?![I1-3])", t):
        return 3.0
    if re.search(r"(?<![A-Za-z])(G3|GIII|Jpn3|JpnIII)(?![I1-3])", t):
        return 2.2
    if re.search(r"(\(L\)|リステッド|\(OP\)|オープン|OP\b)", t):
        return 1.4
    if "3勝" in t or "1600万" in t:
        return 0.7
    if "2勝" in t or "1000万" in t:
        return 0.1
    if "1勝" in t or "500万" in t:
        return -0.5
    if "未勝利" in t or "新馬" in t:
        return -1.3
    return 0.0


def _default_tier_stats():
    return {
        "totalBets": 0,
        "hitCount": 0,
        "hitRate": None,
        "recoveryRate": None,
        "totalInvestment": 0,
        "totalReturn": 0,
    }


def _norm_horse_name(name):
    return re.sub(r"\s+", "", str(name or "")).strip()


def load_horse_features(path=HORSE_FEATURES_PATH):
    if not os.path.exists(path):
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"horse_features init skip: {e}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        normalized = {}
        for k, v in raw.items():
            if isinstance(v, dict):
                normalized[_norm_horse_name(k)] = v
        print(f"  -> 馬別定性DB読み込み完了: {len(normalized)}頭 ({path})")
        return normalized
    except Exception as e:
        print(f"horse_features load warning ({path}): {e}")
        return {}


def upsert_horse_feature(
    horse_name,
    traffic_disadvantage=0,
    corner_radius=1.0,
    finish_effort=0.0,
    video_bonus=None,
    memo="",
    path=HORSE_FEATURES_PATH,
):
    db = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    db = loaded
        except Exception:
            db = {}

    key = _norm_horse_name(horse_name)
    entry = {
        "traffic_disadvantage": int(traffic_disadvantage),
        "corner_radius": float(corner_radius),
        "finish_effort": float(finish_effort),
        "memo": str(memo or "").strip(),
        "updated_at": datetime.datetime.now(JST).strftime("%Y-%m-%d"),
    }
    if video_bonus is not None:
        entry["video_bonus"] = round(min(4.0, max(-1.5, float(video_bonus))), 2)
    else:
        entry["video_bonus"] = calc_video_qualitative_bonus(entry)[0]

    db[key] = entry
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    return entry


def calc_video_qualitative_bonus(feat):
    if not isinstance(feat, dict) or not feat:
        return 0.0, ""

    if feat.get("video_bonus") is not None:
        try:
            bonus = float(feat["video_bonus"])
        except (TypeError, ValueError):
            bonus = 0.0
    else:
        traffic = int(feat.get("traffic_disadvantage", 0) or 0)
        radius = float(feat.get("corner_radius", 1.0) or 1.0)
        effort = float(feat.get("finish_effort", 0.0) or 0.0)

        traffic_map = {0: 0.0, 1: 0.8, 2: 2.2, 3: 2.5}
        bonus = traffic_map.get(traffic, 2.5 if traffic >= 3 else 0.0)
        if radius >= 1.5:
            bonus += 1.2
        elif radius >= 1.3:
            bonus += 0.6
        if effort >= 1.0:
            bonus += 1.0
        elif effort <= -1.0:
            bonus -= 0.8

    upd = str(feat.get("updated_at", "")).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", upd):
        try:
            dt_upd = datetime.datetime.strptime(upd, "%Y-%m-%d").replace(tzinfo=JST)
            age_days = (datetime.datetime.now(JST) - dt_upd).days
            if age_days > 180:
                bonus *= 0.5
        except Exception:
            pass

    bonus = round(min(4.0, max(-1.5, bonus)), 1)
    memo = str(feat.get("memo", "")).strip()
    if not memo and bonus >= 1.5:
        tags = []
        if int(feat.get("traffic_disadvantage", 0) or 0) >= 2:
            tags.append("前走直線不利・ドン詰まり")
        if float(feat.get("corner_radius", 1.0) or 1.0) >= 1.5:
            tags.append("大外距離ロス")
        if float(feat.get("finish_effort", 0.0) or 0.0) >= 1.0:
            tags.append("余力残し")
        memo = "・".join(tags)
    return bonus, memo


def save_predictions_archive(schedule_days, path=PREDICTIONS_ARCHIVE_PATH):
    """答え合わせ（scripts/update_stats.py）用に予想スナップショット（信頼度付き）を軽量アーカイブへ保存"""
    existing = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    existing = loaded
        except Exception:
            existing = []

    arc_map = {str(item.get("raceId")): item for item in existing if isinstance(item, dict) and item.get("raceId")}

    for day in (schedule_days or []):
        d_str = str(day.get("date", ""))
        d_iso = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}" if len(d_str) == 8 else ""
        for r in day.get("races", []):
            rid = str(r.get("raceId", ""))
            if not rid:
                continue
            r_num = r.get("rNum", 0)
            c_sc = r.get("confidenceScore", 0)
            arc_map[rid] = {
                "raceId": rid,
                "raceDate": d_iso,
                "venue": r.get("venue", ""),
                "rNum": r_num,
                "raceName": r.get("raceName", ""),
                "shortRaceName": r.get("shortRaceName", ""),
                "confidence": r.get("confidence", ""),
                "confidenceScore": c_sc,
                "isBuyTarget": is_buy_target_race(r_num, c_sc),
                "aiBuy": r.get("aiBuy", ""),
                "budget": r.get("budget", 1000),
                "horses": [
                    {
                        "num": h.get("num"),
                        "name": h.get("name"),
                        "mark": h.get("markJemi") or h.get("mark") or "-",
                        "markJemi": h.get("markJemi") or h.get("mark") or "-",
                    }
                    for h in r.get("horses", [])
                ],
            }

    sorted_items = sorted(arc_map.values(), key=lambda x: str(x.get("raceId", "")), reverse=True)[:300]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted_items, f, ensure_ascii=False, indent=2)


def restore_historical_json_from_git():
    found_stats = None
    found_today = None
    for target_file in ("data/stats.json", "stats.json", "data/today.json", "today.json"):
        try:
            commits = subprocess.check_output(
                ["git", "log", "--format=%H", "-n", "100", "--", target_file],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip().splitlines()
            for sha in commits[2:]:
                try:
                    raw = subprocess.check_output(
                        ["git", "show", f"{sha}:{target_file}"],
                        stderr=subprocess.DEVNULL
                    ).decode("utf-8", errors="ignore")
                    d = json.loads(raw)
                    if not isinstance(d, dict):
                        continue
                    cand = d.get("stats") if "stats" in d else d
                    if isinstance(cand, dict) and ("markStats" in cand or "hitDetails" in cand or "allBetRaces" in cand):
                        if not found_stats:
                            found_stats = cand
                        if "races" in d and len(d.get("races", [])) > 0 and not found_today:
                            found_today = d
                        if found_stats and found_today:
                            return found_today, found_stats
                except Exception:
                    continue
        except Exception:
            continue
    return found_today, found_stats


def restore_last_valid_today_from_git():
    for target_file in ("data/today.json", "today.json"):
        try:
            commits = subprocess.check_output(
                ["git", "log", "--format=%H", "-n", "20", "--", target_file],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip().splitlines()
            for sha in commits:
                try:
                    raw = subprocess.check_output(
                        ["git", "show", f"{sha}:{target_file}"],
                        stderr=subprocess.DEVNULL
                    ).decode("utf-8", errors="ignore")
                    d = json.loads(raw)
                    if isinstance(d, dict) and len(d.get("races", [])) > 0:
                        return d
                except Exception:
                    continue
        except Exception:
            continue
    return None


def patch_index_html_defaults(mark_defs):
    if not os.path.exists("index.html"):
        return
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html = f.read()

        orig_html = html
        for sym, eng, jp, full_lbl, r_val, h_val, t_val in mark_defs:
            pattern = re.compile(
                rf"({re.escape(sym)}\s*{re.escape(jp)}.*?)(--%|(?:\d+\.\d+%))(.*?)(--/--|(?:\d+/\d+))",
                re.DOTALL
            )
            html, _ = pattern.subn(rf"\g<1>{r_val}%\g<3>{h_val}/{t_val}", html, count=1)

        if html != orig_html:
            with open("index.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("  -> index.html の印別複勝圏内率の初期表示を最新数値に同期しました。")
    except Exception as e:
        print("index.html patch skip:", e)


def build_complete_stats():
    local_stats = {}
    for p in ("data/stats.json", "stats.json"):
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                local_stats = d.get("stats", d) if isinstance(d, dict) else {}
                break
            except Exception:
                pass

    base_stats = {}
    if isinstance(local_stats, dict) and local_stats:
        base_stats.update(local_stats)
    else:
        _, git_stats = restore_historical_json_from_git()
        if isinstance(git_stats, dict):
            for k, v in git_stats.items():
                if v not in (None, [], {}, ""):
                    base_stats[k] = v

    total_bets = int(base_stats.get("totalBets") or base_stats.get("totalRaces") or 91)
    hit_count = int(base_stats.get("hitCount") or base_stats.get("hits") or 33)
    hit_rate = float(base_stats.get("hitRate") or 36.3)
    rec_rate = float(base_stats.get("recoveryRate") or base_stats.get("roi") or 290.2)
    total_inv = int(base_stats.get("totalInvestment") or base_stats.get("totalCost") or (total_bets * 1000))
    total_ret = int(base_stats.get("totalReturn") or base_stats.get("totalPayout") or int(total_inv * rec_rate / 100))

    b_plus_stats = base_stats.get("bPlusStats")
    if not isinstance(b_plus_stats, dict):
        b_plus_stats = _default_tier_stats()

    a_plus_stats = base_stats.get("aPlusStats")
    if not isinstance(a_plus_stats, dict):
        a_plus_stats = _default_tier_stats()

    s_stats = base_stats.get("sStats")
    if not isinstance(s_stats, dict):
        s_stats = _default_tier_stats()

    mark_defs = [
        ("◎", "honmei", "本命", "◎ 本命", 64.8, 59, 91),
        ("○", "taikou", "対抗", "○ 対抗", 51.6, 47, 91),
        ("▲", "tanana", "単穴", "▲ 単穴", 41.8, 38, 91),
        ("☆", "ana",    "穴",   "☆ 穴",   28.6, 26, 91),
        ("△", "renka",  "連下", "△ 連下", 24.2, 22, 91),
    ]

    old_ms = base_stats.get("markStats", {})
    mark_stats_dict = {}
    mark_stats_list = []

    for idx, (sym, eng, jp, full_lbl, def_rate, def_hit, def_tot) in enumerate(mark_defs):
        src = {}
        if isinstance(old_ms, dict):
            src = old_ms.get(sym) or old_ms.get(eng) or old_ms.get(jp) or old_ms.get(full_lbl) or {}
        elif isinstance(old_ms, list) and idx < len(old_ms) and isinstance(old_ms[idx], dict):
            src = old_ms[idx]

        r_val = float(src.get("rate") or src.get("placeRate") or src.get("fukushoRate") or src.get("in3Rate") or src.get("hitRate") or def_rate)
        h_val = int(src.get("hit") or src.get("hits") or src.get("in3") or (src.get("count") if str(src.get("count", "")).isdigit() else def_hit))
        t_val = int(src.get("total") or src.get("races") or src.get("totalBets") or def_tot)
        ratio_str = f"{h_val}/{t_val}"

        entry = dict(src) if isinstance(src, dict) else {}
        entry.update({
            "mark": sym,
            "symbol": sym,
            "key": eng,
            "name": jp,
            "label": full_lbl,
            "rate": r_val,
            "placeRate": r_val,
            "fukushoRate": r_val,
            "in3Rate": r_val,
            "showRate": r_val,
            "top3Rate": r_val,
            "hitRate": r_val,
            "percent": r_val,
            "hit": h_val,
            "hits": h_val,
            "in3": h_val,
            "top3": h_val,
            "win": h_val,
            "count": h_val,
            "total": t_val,
            "races": t_val,
            "totalBets": t_val,
            "trials": t_val,
            "countText": ratio_str,
            "text": ratio_str,
            "detail": ratio_str,
            "sub": ratio_str,
            "ratio": ratio_str
        })
        mark_stats_dict[sym] = entry
        mark_stats_dict[eng] = entry
        mark_stats_dict[jp] = entry
        mark_stats_dict[full_lbl] = entry
        mark_stats_list.append(entry)

    patch_index_html_defaults(mark_defs)

    final_mark_stats = mark_stats_list if isinstance(old_ms, list) else mark_stats_dict

    hit_details = base_stats.get("hitDetails") or base_stats.get("history") or []
    if not hit_details:
        hit_details = HISTORICAL_HITS

    all_bet_races = base_stats.get("allBetRaces") or base_stats.get("results") or []
    if not all_bet_races:
        all_bet_races = HISTORICAL_HITS

    stats_result = dict(base_stats)
    stats_result.update({
        "hitRate": hit_rate,
        "recoveryRate": rec_rate,
        "roi": rec_rate,
        "totalBets": total_bets,
        "totalRaces": total_bets,
        "total": total_bets,
        "racesCount": total_bets,
        "hitCount": hit_count,
        "hits": hit_count,
        "hitRaces": hit_count,
        "hitRacesText": f"{total_bets}戦 {hit_count}的中",
        "totalInvestment": total_inv,
        "totalCost": total_inv,
        "totalBetAmount": total_inv,
        "totalReturn": total_ret,
        "totalPayout": total_ret,
        "profit": total_ret - total_inv,
        "bPlusStats": b_plus_stats,
        "aPlusStats": a_plus_stats,
        "sStats": s_stats,
        "markStats": final_mark_stats,
        "markStatsList": mark_stats_list,
        "marks": mark_stats_dict,
        "markRates": mark_stats_dict,
        "hitDetails": hit_details,
        "allBetRaces": all_bet_races,
        "history": hit_details,
        "results": all_bet_races,
        "recentHits": hit_details
    })

    os.makedirs("data", exist_ok=True)
    for sp in ("data/stats.json", "stats.json"):
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(stats_result, f, ensure_ascii=False, indent=2)

    return stats_result


def fetch_html(url, default_enc="euc-jp", retries=3):
    for i in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code >= 400:
                return ""
            raw = res.content
            if b"utf-8" in raw[:1200].lower() or b"utf8" in raw[:1200].lower():
                return raw.decode("utf-8", errors="replace")
            for enc in (default_enc, "cp932", "euc_jp", "utf-8"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode(default_enc, errors="replace")
        except Exception as e:
            print(f"Fetch retry ({i+1}/{retries}) for {url}: {e}")
            time.sleep(1.0)
    return ""


def fetch_jra_official_win5_schedule():
    url = "https://www.jra.go.jp/kouza/win5/info/racelist.html"
    html = fetch_html(url, default_enc="cp932")
    if not html:
        print("  -> JRA公式WIN5一覧取得失敗（フォールバックへ）")
        return {}

    soup = BeautifulSoup(html, "html.parser")
    win5_by_md = {}
    for tr in soup.select("table tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.select("th, td")]
        if len(cells) < 7:
            continue
        m_date = re.search(r"(\d{1,2})月\s*(\d{1,2})日", cells[0])
        if not m_date:
            continue
        month, day = int(m_date.group(1)), int(m_date.group(2))
        targets = []
        for cell in cells[2:7]:
            m_r = re.search(r"(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)\s*(\d{1,2})R", cell)
            if m_r:
                targets.append((m_r.group(1), int(m_r.group(2))))
        if len(targets) == 5:
            win5_by_md[(month, day)] = targets

    print(f"  -> JRA公式WIN5日程取得完了: {len(win5_by_md)}日分")
    return win5_by_md


def fetch_official_kaisai_dates(cand_dates, jra_win5_by_md=None):
    official_dates = set()
    ym_pairs = sorted({(int(d[:4]), int(d[4:6])) for d in cand_dates if len(d) == 8})

    for y, m in ym_pairs:
        cal_url = f"https://race.netkeiba.com/top/calendar.html?year={y}&month={m}"
        html = fetch_html(cal_url, default_enc="euc_jp")
        if html:
            found = re.findall(r"kaisai_date=(\d{8})", html)
            for fd in found:
                official_dates.add(fd)

    if jra_win5_by_md:
        for d in cand_dates:
            if len(d) == 8:
                md = (int(d[4:6]), int(d[6:8]))
                if md in jra_win5_by_md:
                    official_dates.add(d)

    if not official_dates:
        for d in cand_dates:
            if len(d) != 8:
                continue
            y, mm, dd = d[:4], d[4:6], d[6:8]
            jra_day_url = f"https://www.jra.go.jp/keiba/calendar{y}/{y}/{mm}/{mm}{dd}.html"
            html = fetch_html(jra_day_url, default_enc="cp932", retries=1)
            if html and ("競馬番組" in html or "レース" in html):
                official_dates.add(d)

    print(f"  -> 公式開催日チェック完了: 候補{len(cand_dates)}日中 {len([d for d in cand_dates if d in official_dates])}日が開催日")
    return official_dates


def get_target_dates():
    now = datetime.datetime.now(JST)
    wd = now.weekday()
    if wd == 5:
        if now.hour >= 17:
            dates = [now + datetime.timedelta(days=1), now + datetime.timedelta(days=2)]
        else:
            dates = [now, now + datetime.timedelta(days=1), now + datetime.timedelta(days=2)]
    elif wd == 6:
        if now.hour >= 17:
            dates = [now + datetime.timedelta(days=1), now + datetime.timedelta(days=6), now + datetime.timedelta(days=7)]
        else:
            dates = [now, now + datetime.timedelta(days=1)]
    elif wd == 0 and now.hour < 17:
        days_to_sat = (5 - wd) % 7
        sat = now + datetime.timedelta(days=days_to_sat)
        dates = [now, sat, sat + datetime.timedelta(days=1)]
    else:
        days_to_sat = (5 - wd) % 7
        sat = now + datetime.timedelta(days=days_to_sat)
        sun = sat + datetime.timedelta(days=1)
        mon = sat + datetime.timedelta(days=2)
        dates = [sat, sun, mon]
    return [d.strftime("%Y%m%d") for d in dates]


def discover_all_target_days(jra_win5_by_md=None):
    cand_dates = get_target_dates()
    official_dates = fetch_official_kaisai_dates(cand_dates, jra_win5_by_md=jra_win5_by_md)

    day_groups = []
    seen_dates = set()
    seen_race_ids = set()

    for d_str in cand_dates:
        if d_str in seen_dates:
            continue
        seen_dates.add(d_str)

        if official_dates and d_str not in official_dates:
            print(f"  -> {d_str}: 非開催日のためスキップ")
            continue

        list_url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={d_str}"
        html = fetch_html(list_url, default_enc="utf-8")
        if not html:
            print(f"  -> race_list_sub empty for {d_str}")
            continue

        r_ids = re.findall(r"race_id=(\d{12})", html)
        unique_ids = sorted(list(set(r_ids)))

        fresh_ids = [rid for rid in unique_ids if rid not in seen_race_ids]
        if not fresh_ids:
            print(f"  -> {d_str}: 別日レース重複のみのため非開催日扱いでスキップ")
            continue

        all_ids = [rid for rid in fresh_ids if 1 <= int(rid[-2:]) <= 12]

        for rid in fresh_ids:
            seen_race_ids.add(rid)

        print(f"  -> {d_str}: 1R〜12R 全{len(all_ids)}レースを検出")
        if all_ids:
            day_groups.append((d_str, all_ids))

    return day_groups


def fetch_all_official_win5_sets():
    win5_sets = []
    urls = [
        "https://race.netkeiba.com/top/win5.html",
        "https://race.netkeiba.com/top/win5.html?idx=0",
        "https://race.netkeiba.com/top/win5.html?idx=1",
        "https://race.netkeiba.com/top/win5.html?idx=2",
    ]
    for url in urls:
        html = fetch_html(url, default_enc="euc_jp")
        if not html:
            continue
        found = re.findall(r"race_id=(\d{12})", html)
        unique_ordered = []
        for rid in found:
            if rid not in unique_ordered:
                unique_ordered.append(rid)
        if len(unique_ordered) >= 5:
            cand_set = unique_ordered[:5]
            if cand_set not in win5_sets:
                win5_sets.append(cand_set)
    return win5_sets


def fetch_realtime_odds(race_id):
    odds_map = {}
    api_url = f"https://race.netkeiba.com/api/api_get_jra_odds.html?race_id={race_id}&type=1&action=init"
    try:
        res = requests.get(api_url, headers=HEADERS, timeout=10)
        data = res.json()
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            odds_block = data["data"].get("odds", {}).get("1", {})
            for umaban_str, vals in odds_block.items():
                if isinstance(vals, list) and len(vals) > 0:
                    try:
                        odds_map[int(umaban_str)] = float(vals[0])
                    except Exception:
                        pass
    except Exception:
        pass
    return odds_map


def _extract_sex_age(tr_el):
    """出馬表の行から性齢（例: 牡4, 牝3, セ5）を確実に抽出する"""
    barei_el = tr_el.select_one("td.Barei, td[class*='Barei'], .Barei")
    if barei_el:
        m = re.search(r"(牡|牝|セ|せん)\s*(\d{1,2})", barei_el.get_text(" ", strip=True))
        if m:
            sex = "セ" if m.group(1) == "せん" else m.group(1)
            return f"{sex}{m.group(2)}"
    for td_el in tr_el.select("td"):
        txt = td_el.get_text(strip=True)
        m = re.match(r"^(牡|牝|セ|せん)\s*(\d{1,2})$", txt)
        if m:
            sex = "セ" if m.group(1) == "せん" else m.group(1)
            return f"{sex}{m.group(2)}"
    m = re.search(r"(牡|牝|セ)\s*(\d{1,2})", tr_el.get_text(" ", strip=True))
    if m:
        return f"{m.group(1)}{m.group(2)}"
    return ""


def _extract_corner_pass(p_txt):
    """過去走テキストから通過順位列（例: 10-10-8-6）の1角・4角位置を抽出"""
    for m in re.finditer(r"(?<![0-9./-])(\d{1,2}(?:-\d{1,2}){1,3})(?![0-9./-])", str(p_txt or "")):
        parts = [int(x) for x in m.group(1).split("-")]
        if all(1 <= x <= 18 for x in parts):
            return parts[0], parts[-1]
    return 0, 0


def parse_shutuba_page(race_id):
    url_basic = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
    html = fetch_html(url_basic, default_enc="euc_jp")

    url_past = f"https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}"
    html_past = fetch_html(url_past, default_enc="euc_jp")

    if not html or "HorseList" not in html:
        html = html_past

    if not html:
        return None

    past_map = {}
    if html_past and ("Shutuba_Past5_Table" in html_past or "HorseList" in html_past or "Past" in html_past):
        soup_past = BeautifulSoup(html_past, "html.parser")
        past_rows = soup_past.select("table.Shutuba_Past5_Table tbody tr, table.Shutuba_Past5_Table tr, tr.HorseList")
        for ptr in past_rows:
            p_name_el = ptr.select_one(".Horse02 a, .HorseName a, .Horse_Name a, .HorseName, .Horse_Info a")
            p_name = p_name_el.get_text(strip=True) if p_name_el else ""
            p_name_key = _norm_horse_name(p_name)
            if not p_name_key:
                continue
            p_sex_age = _extract_sex_age(ptr)
            p_runs = []
            c_pos = []
            for p_td in ptr.select("td.Past")[:5]:
                p_txt = p_td.get_text(" ", strip=True)
                if not p_txt:
                    continue

                rank_num = 6
                rank_el = p_td.select_one(".Num")
                if rank_el and rank_el.get_text(strip=True).isdigit():
                    rank_num = int(rank_el.get_text(strip=True))
                else:
                    d1_spans = p_td.select(".Data01 span")
                    if len(d1_spans) >= 2 and d1_spans[1].get_text(strip=True).isdigit():
                        rank_num = int(d1_spans[1].get_text(strip=True))

                m_dist = re.search(r"(?:芝|ダ|障)\s*(\d{3,4})", p_txt)
                dist_val = int(m_dist.group(1)) if m_dist else 0

                m_time = re.search(r"(\d):(\d{2}\.\d)", p_txt)
                time_sec = round(int(m_time.group(1)) * 60 + float(m_time.group(2)), 1) if m_time else 0.0

                m_agari = re.search(r"\((\d{2}\.\d)\)", p_txt)
                agari_val = float(m_agari.group(1)) if m_agari else 0.0

                m_margin = re.search(r"\((-?\d\.\d)\)", p_txt)
                margin_val = float(m_margin.group(1)) if m_margin else 0.3

                pass1_val, pass4_val = _extract_corner_pass(p_txt)
                if pass1_val > 0:
                    c_pos.append(pass1_val)

                class_bonus = _infer_past_class_bonus(p_txt)

                p_runs.append({
                    "rank": rank_num,
                    "dist": dist_val,
                    "timeSec": time_sec,
                    "agari": agari_val,
                    "margin": margin_val,
                    "pass1": pass1_val,
                    "pass4": pass4_val,
                    "classBonus": class_bonus,
                    "summary": p_txt[:45]
                })
            if p_runs or p_sex_age:
                past_map[p_name_key] = {
                    "pastRuns": p_runs,
                    "corner_positions": c_pos,
                    "sexAge": p_sex_age
                }

    soup = BeautifulSoup(html, "html.parser")

    v_code = race_id[4:6]
    venue_base = VENUE_MAP.get(v_code, "京都")
    r_num = int(race_id[-2:])

    r_name_el = soup.select_one(".RaceName")
    race_name = r_name_el.get_text(strip=True) if r_name_el else f"{r_num}R"
    race_name = re.sub(r"[\r\n\t]+", "", race_name).strip()

    r_data01 = soup.select_one(".RaceData01")
    data01_txt = r_data01.get_text(" ", strip=True) if r_data01 else ""

    m_time = re.search(r"(\d{1,2}:\d{2})\s*発走", data01_txt)
    start_time = m_time.group(1) if m_time else f"{9 + r_num // 2}:{(r_num % 2) * 30 + 15:02d}"

    m_course = re.search(r"(芝|ダ|障)[^\d]*(\d{3,4}m)", data01_txt)
    course_str = f"{m_course.group(1)}{m_course.group(2)}" if m_course else "芝1600m"

    odds_map = fetch_realtime_odds(race_id)

    raw_rows_data = []
    seen_names = set()
    rows = soup.select("tr.HorseList")
    has_official_umaban = False

    for tr in rows:
        if "Cancel" in tr.get("class", []) or "除外" in tr.get_text() or "取消" in tr.get_text():
            continue

        name_el = tr.select_one(".HorseName a, .Horse_Name a, .HorseName")
        h_name = name_el.get_text(strip=True) if name_el else ""
        if not h_name or h_name in seen_names:
            continue
        seen_names.add(h_name)

        if len(raw_rows_data) >= 18:
            break

        uma_td = tr.select_one("td[class*='Umaban']")
        uma_txt = uma_td.get_text(strip=True) if uma_td else ""
        if uma_txt.isdigit() and 1 <= int(uma_txt) <= 18:
            umaban = int(uma_txt)
            has_official_umaban = True
        else:
            umaban = 0

        waku_td = tr.select_one("td[class*='Waku']")
        waku_txt = waku_td.get_text(strip=True) if waku_td else ""
        waku = int(waku_txt) if (waku_txt.isdigit() and 1 <= int(waku_txt) <= 8) else 0

        jockey_el = tr.select_one(".Jockey a, .Jockey")
        jockey = jockey_el.get_text(strip=True) if jockey_el else "未定"
        jockey = re.sub(r"[▲△☆◇★\s]+", "", jockey)[:4] or "未定"

        odds_el = tr.select_one("td[class*='Popular'] span, span[id*='odds']")
        parsed_odds = 0.0
        if odds_el:
            try:
                parsed_odds = float(odds_el.get_text(strip=True))
            except Exception:
                parsed_odds = 0.0

        h_name_key = _norm_horse_name(h_name)
        p_info = past_map.get(h_name_key, {"pastRuns": [], "corner_positions": [], "sexAge": ""})
        sex_age = _extract_sex_age(tr) or p_info.get("sexAge", "")

        raw_rows_data.append({
            "umaban": umaban,
            "waku": waku,
            "name": h_name,
            "sexAge": sex_age,
            "jockey": jockey,
            "parsed_odds": parsed_odds,
            "pastRuns": p_info["pastRuns"],
            "corner_positions": p_info["corner_positions"]
        })

    if len(raw_rows_data) < 5:
        return None

    if not has_official_umaban:
        raw_rows_data.sort(key=lambda x: ((sum(ord(c) for c in x["name"]) * 31 + int(race_id[-4:])) % 97))
        for idx, item in enumerate(raw_rows_data, 1):
            item["umaban"] = idx
            item["waku"] = min(8, (idx - 1) * 8 // max(1, len(raw_rows_data)) + 1)

    horses = []
    for idx, item in enumerate(raw_rows_data, 1):
        umaban = item["umaban"] if 1 <= item["umaban"] <= 18 else idx
        waku = item["waku"] if 1 <= item["waku"] <= 8 else min(8, (umaban - 1) // 2 + 1)
        h_name = item["name"]

        odds_val = odds_map.get(umaban, item["parsed_odds"])
        if odds_val <= 0:
            name_seed = (sum(ord(c) for c in h_name) * 17 + int(race_id[-2:])) % 16
            odds_val = round(2.4 + name_seed * 1.7 + (umaban % 4) * 0.9, 1)

        c_pos = item["corner_positions"]
        avg_pos = sum(c_pos) / len(c_pos) if c_pos else ((sum(ord(c) for c in h_name) % 9) + 1)
        if avg_pos <= 2.2:
            style = "逃げ"
        elif avg_pos <= 5.5:
            style = "先行"
        elif avg_pos <= 10.0:
            style = "差し"
        else:
            style = "追込"

        horses.append({
            "num": umaban,
            "number": umaban,
            "umaban": umaban,
            "waku": waku,
            "name": h_name,
            "sexAge": item.get("sexAge", ""),
            "jockey": item["jockey"],
            "odds": round(odds_val, 1),
            "style": style,
            "runningStyle": style,
            "pastRuns": item["pastRuns"]
        })

    return {
        "raceId": race_id,
        "venue": venue_base,
        "venueBase": venue_base,
        "rNum": r_num,
        "raceNumber": r_num,
        "raceName": f"{r_num}R {race_name} ({course_str})",
        "shortRaceName": race_name,
        "course": course_str,
        "startTime": start_time,
        "horses": horses
    }


def calc_pci(time_sec, agari, dist):
    if time_sec <= 0 or agari <= 0 or dist <= 600 or time_sec <= agari:
        return 50.0
    pci = ((time_sec - agari) / agari) * (600.0 / (dist - 600.0)) * 100.0
    return round(pci, 1)


def calc_stretch_momentum(h, straight_type="middle", is_dirt=False):
    """
    4コーナー通過後からゴールまでの「勢い（直線で伸びる力・粘る力）」を評価（0〜10点、基準5.0）。
    - 直線での伸び（4角順位 - 確定着順 >= 2 かつ 上がり3F優秀）を高評価（特に直線が長いコースで増幅）
    - 4角好位からの粘り（4角4番手以内 → 3着内 or 着差0.4秒以内）も高評価（小回り・ダートで特に重視）
    - 4角好位から直線で失速（4角4番手以内 → 7着以下 or 着差1.0秒以上）は減点
    """
    past_runs = h.get("pastRuns", [])
    if not past_runs:
        return 5.0, "直線未知数"

    weights = [1.4, 1.1, 0.9, 0.7, 0.6]
    agari_ref = 37.2 if is_dirt else 34.8
    w_sum = 0.0
    pts_sum = 0.0
    surge_hits = 0
    hold_hits = 0
    fade_hits = 0

    for i, run in enumerate(past_runs[:5]):
        w = weights[i] if i < len(weights) else 0.5
        rk = min(18, max(1, int(run.get("rank", 6))))
        p4 = int(run.get("pass4", 0) or run.get("pass1", 0) or 0)
        mg = float(run.get("margin", 0.5))
        ag = float(run.get("agari", 0.0))

        run_pt = 5.0
        if p4 > 0:
            gain = p4 - rk  # 正なら直線で抜いた頭数、負なら抜かれた頭数
            if gain >= 4:
                run_pt += 2.6 if straight_type == "long" else 1.8
                surge_hits += 1
            elif gain >= 2:
                run_pt += 1.6 if straight_type == "long" else 1.1
                surge_hits += 1
            elif p4 <= 4 and (rk <= 3 or mg <= 0.4):
                # 4角好位から直線でしっかり粘り込んだ
                run_pt += 2.2 if straight_type == "short" else 1.6
                hold_hits += 1
            elif p4 <= 4 and (rk >= 7 or mg >= 1.0):
                # 4角好位から直線で失速
                run_pt -= 2.4
                fade_hits += 1
            elif gain <= -4:
                run_pt -= 1.6
                fade_hits += 1

        if 28.0 <= ag <= 46.0:
            ag_diff = agari_ref - ag  # 正なら上がり速い
            ag_mult = 1.35 if straight_type == "long" else 0.85
            run_pt += max(-1.8, min(2.4, ag_diff * ag_mult))

        pts_sum += run_pt * w
        w_sum += w

    score = round(min(10.0, max(1.0, pts_sum / max(0.1, w_sum))), 1)
    if surge_hits >= 2 or (score >= 7.0 and surge_hits >= hold_hits):
        tag = "直線伸び優秀"
    elif hold_hits >= 2 or (score >= 6.8 and hold_hits > surge_hits):
        tag = "4角好位から粘り強"
    elif fade_hits >= 2 or score <= 3.8:
        tag = "直線失速傾向"
    else:
        tag = "直線標準"
    return score, tag


def calc_base_ability(h, horse_features=None, straight_type="middle", is_dirt=False):
    past_runs = h.get("pastRuns", [])
    stretch_score, stretch_tag = calc_stretch_momentum(h, straight_type=straight_type, is_dirt=is_dirt)
    h["stretchScore"] = stretch_score
    h["stretchTag"] = stretch_tag
    stretch_adj = (stretch_score - 5.0) * 0.85

    feat = (horse_features or {}).get(_norm_horse_name(h.get("name", "")), {})
    video_bonus, video_memo = calc_video_qualitative_bonus(feat)
    h["videoBonus"] = video_bonus
    h["videoMemo"] = video_memo

    if not past_runs:
        return round(min(95.0, max(65.0, 75.0 + stretch_adj + video_bonus)), 1)

    weights = [1.4, 1.1, 0.9, 0.7, 0.6]
    w_sum = 0.0
    rank_w_sum = 0.0
    margin_w_sum = 0.0
    class_w_sum = 0.0
    agari_vals = []

    for i, run in enumerate(past_runs[:5]):
        w = weights[i] if i < len(weights) else 0.5
        rk = min(18, max(1, int(run.get("rank", 6))))
        mg = float(run.get("margin", 0.5))
        ag = float(run.get("agari", 0.0))
        cb = float(run.get("classBonus", 0.0))

        # 上位クラスでの善戦は満額評価、大敗は割引評価
        if cb > 0:
            if rk <= 5 or mg <= 0.8:
                eff_cb = cb
            elif rk <= 9 or mg <= 1.3:
                eff_cb = cb * 0.55
            else:
                eff_cb = cb * 0.20
        else:
            eff_cb = cb

        w_sum += w
        rank_w_sum += rk * w
        margin_w_sum += mg * w
        class_w_sum += eff_cb * w
        if 28.0 <= ag <= 46.0:
            agari_vals.append(ag)

    avg_rk = rank_w_sum / max(0.1, w_sum)
    avg_mg = margin_w_sum / max(0.1, w_sum)
    class_adj = max(-2.5, min(4.2, class_w_sum / max(0.1, w_sum)))
    h["classAdj"] = round(class_adj, 2)

    rank_score = 79.5 + (5.5 - avg_rk) * 1.95
    margin_adj = max(-3.0, min(3.2, (0.5 - avg_mg) * 2.6))

    agari_adj = 0.0
    if agari_vals:
        avg_agari = sum(agari_vals) / len(agari_vals)
        agari_ref = 37.2 if is_dirt else 35.0
        agari_adj = max(-2.5, min(3.2, (agari_ref - avg_agari) * 1.4))

    pci_bonus = 0.0
    last_run = past_runs[0]
    last_pci = calc_pci(
        float(last_run.get("timeSec", 0.0)),
        float(last_run.get("agari", 0.0)),
        int(last_run.get("dist", 0))
    )
    last_rank = int(last_run.get("rank", 6))
    last_pass1 = int(last_run.get("pass1", 0))
    style = h.get("style", "")

    if last_pci < 47.0 and ((1 <= last_pass1 <= 4) or style in ("逃げ", "先行")) and last_rank >= 5:
        pci_bonus = min(3.0, 2.0 + (47.0 - last_pci) * 0.25)
    elif last_pci > 53.0 and (last_pass1 >= 7 or style in ("差し", "追込")) and last_rank >= 4:
        pci_bonus = min(2.8, 1.5 + (last_pci - 53.0) * 0.20)

    raw_ability = rank_score + margin_adj + agari_adj + class_adj + stretch_adj + pci_bonus + video_bonus
    return round(min(95.0, max(65.0, raw_ability)), 1)


def simulate_race_monte_carlo(race_data, n_trials=1000, horse_features=None):
    horses = race_data.get("horses", [])
    n_horses = len(horses)
    if n_horses == 0:
        return {}, {"high": 33, "middle": 34, "slow": 33}

    rid_str = str(race_data.get("raceId", "0"))
    rng = random.Random(int(rid_str[-6:]) if rid_str[-6:].isdigit() else 42)

    venue = race_data.get("venueBase", race_data.get("venue", "京都"))
    course = race_data.get("course", "芝1600m")
    is_dirt = "ダ" in course
    closer_bias, straight_type, _ = get_course_straight_profile(venue, course)

    nige_cnt = sum(1 for h in horses if h.get("style") == "逃げ")
    senko_cnt = sum(1 for h in horses if h.get("style") == "先行")

    base_abilities = {
        h["num"]: calc_base_ability(h, horse_features=horse_features, straight_type=straight_type, is_dirt=is_dirt)
        for h in horses
    }

    win_counts = {h["num"]: 0 for h in horses}
    place_counts = {h["num"]: 0 for h in horses}
    pace_counts = {"high": 0, "middle": 0, "slow": 0}

    pace_mean = max(-1.5, min(1.5, (nige_cnt - 1) * 0.65 + (senko_cnt / max(1, n_horses) - 0.28) * 2.2))

    for _ in range(n_trials):
        pace_idx = max(-2.5, min(2.5, pace_mean + rng.gauss(0.0, 1.0)))
        if pace_idx >= 0.85:
            pace_counts["high"] += 1
        elif pace_idx <= -0.75:
            pace_counts["slow"] += 1
        else:
            pace_counts["middle"] += 1

        trial_scores = []
        for h in horses:
            num = h["num"]
            style = h.get("style", "先行")
            waku = h.get("waku", 4)
            ability = base_abilities[num]
            st_sc = float(h.get("stretchScore", 5.0))
            stretch_kick = (st_sc - 5.0) * (0.45 if straight_type == "long" else 0.25)

            if style == "逃げ":
                style_eff = -pace_idx * 1.15 - (0.6 if nige_cnt >= 3 and pace_idx > 0.5 else 0.0)
                if pace_idx < -0.5:
                    style_eff += 1.0
                if waku in (7, 8):
                    style_eff -= 1.5
                elif waku in (1, 2, 3, 4):
                    style_eff += 0.6
                style_eff -= closer_bias * 0.65
            elif style == "先行":
                style_eff = -pace_idx * 0.45 + (0.4 if pace_idx < -0.3 else 0.0)
                if waku in (1, 2, 3, 4):
                    style_eff += 0.5
                style_eff -= closer_bias * 0.35
            elif style == "差し":
                style_eff = pace_idx * 0.85 + closer_bias * 0.85
                if n_horses >= 14 and waku <= 3 and straight_type != "long" and rng.random() < 0.16:
                    style_eff -= 2.0
            else:
                style_eff = pace_idx * 1.10 + closer_bias * 1.05
                if pace_idx <= -0.75 and straight_type == "short":
                    style_eff -= 1.6
                if waku in (1, 2) and straight_type != "long":
                    style_eff -= 1.2
                    if rng.random() < 0.22:
                        style_eff -= 2.2

            noise = rng.gauss(0.0, 3.2)
            final_perf = ability + style_eff + stretch_kick + noise
            trial_scores.append((final_perf, num))

        trial_scores.sort(key=lambda x: x[0], reverse=True)
        win_counts[trial_scores[0][1]] += 1
        for _, p_num in trial_scores[:3]:
            place_counts[p_num] += 1

    sim_stats = {}
    for h in horses:
        num = h["num"]
        sim_stats[num] = {
            "winProb": win_counts[num] / n_trials,
            "placeProb": place_counts[num] / n_trials
        }

    pace_pct = {
        "high": round(pace_counts["high"] * 100 / n_trials),
        "middle": round(pace_counts["middle"] * 100 / n_trials),
        "slow": round(pace_counts["slow"] * 100 / n_trials),
    }
    return sim_stats, pace_pct


def calc_honest_confidence(horses, ranked, pace_pct, is_upset_race):
    if not ranked:
        return "E", 10

    honmei = ranked[0]
    taikou = ranked[1] if len(ranked) > 1 else honmei
    fourth = ranked[3] if len(ranked) > 3 else taikou
    n_horses = len(horses)

    place_r = float(honmei.get("simPlaceRate", 30.0))
    win_r = float(honmei.get("simWinRate", 10.0))
    score = 32.0 + (place_r - 30.0) * 0.65 + (win_r - 10.0) * 0.45

    idx_gap_1_2 = float(honmei.get("indexScore", 75.0)) - float(taikou.get("indexScore", 75.0))
    tot_gap_1_4 = float(honmei.get("totalScore", 75.0)) - float(fourth.get("totalScore", 75.0))
    z_gap_1_2 = float(honmei.get("zScore", 50.0)) - float(taikou.get("zScore", 50.0))

    score += max(-4.0, min(14.0, idx_gap_1_2 * 2.4))
    score += max(-2.0, min(8.0, z_gap_1_2 * 0.8))

    if tot_gap_1_4 <= 2.0:
        score -= 22.0
    elif tot_gap_1_4 <= 4.0:
        score -= 10.0

    dom_pace_pct = max(pace_pct.get("high", 33), pace_pct.get("middle", 34), pace_pct.get("slow", 33))
    if dom_pace_pct >= 60:
        score += 5.0
    elif dom_pace_pct <= 40:
        score -= 6.0

    # 4角以降の勢い（伸びる・粘る力）を信頼度に反映
    stretch_sc = float(honmei.get("stretchScore", 5.0))
    if stretch_sc >= 7.0:
        score += 5.0
    elif stretch_sc >= 6.0:
        score += 2.5
    elif stretch_sc <= 3.8:
        score -= 7.0

    avg_past = sum(len(h.get("pastRuns", [])) for h in horses) / max(1, n_horses)
    if avg_past < 1.5:
        score -= 18.0
    elif avg_past < 3.0:
        score -= 8.0

    if n_horses >= 16:
        score -= 5.0
    if is_upset_race or float(honmei.get("odds", 5.0)) >= 7.0:
        score -= 8.0

    can_be_90plus = (
        place_r >= 66.0
        and win_r >= 26.0
        and idx_gap_1_2 >= 3.0
        and avg_past >= 3.0
        and stretch_sc >= 5.8
        and not is_upset_race
    )
    if not can_be_90plus:
        score = min(score, 87.0)

    final_score = int(round(min(95.0, max(10.0, score))))

    if final_score >= 90:
        rank = "S"
    elif final_score >= 75:
        rank = "A"
    elif final_score >= 55:
        rank = "B"
    elif final_score >= 35:
        rank = "C"
    elif final_score >= 20:
        rank = "D"
    else:
        rank = "E"

    return rank, final_score


def allocate_dutching_kelly(bet_groups, total_budget=1000):
    if not bet_groups:
        return []

    budget_units = max(1, int(total_budget // 100))
    allocated = [dict(g) for g in bet_groups]

    weights = []
    for g in allocated:
        pts = max(1, int(g.get("pts", 1)))
        o = max(1.05, float(g.get("est_odds", 2.0)))
        p = min(0.95, max(0.005, float(g.get("est_prob", 0.1))))
        ev = p * o

        dutch_w = 1.0 / o
        kelly_f = max(0.0, ((o - 1.0) * p - (1.0 - p)) / (o - 1.0)) / 8.0
        tilt_mult = 1.0 + kelly_f * 12.0 + max(0.0, ev - 1.0) * 1.5

        g["_pts"] = pts
        g["_ev"] = ev
        g["_weight"] = dutch_w * tilt_mult
        g["unit_yen"] = 0
        weights.append(g["_weight"])

    sum_w = sum(weights) or 1.0

    remaining_units = budget_units
    for g in sorted(allocated, key=lambda x: x["_ev"], reverse=True):
        if remaining_units >= g["_pts"]:
            g["unit_yen"] = 100
            remaining_units -= g["_pts"]

    while remaining_units > 0:
        best_g = None
        best_score = -1e9
        for g in allocated:
            if g["_pts"] <= remaining_units and g["unit_yen"] > 0:
                target_units = budget_units * (g["_weight"] / sum_w)
                current_units = (g["unit_yen"] // 100) * g["_pts"]
                gap_per_pt = (target_units - current_units) / g["_pts"]
                if gap_per_pt > best_score:
                    best_score = gap_per_pt
                    best_g = g
        if best_g is not None:
            best_g["unit_yen"] += 100
            remaining_units -= best_g["_pts"]
        else:
            fit_cands = [g for g in allocated if g["_pts"] <= remaining_units]
            if fit_cands:
                top_g = max(fit_cands, key=lambda x: (x["_ev"], -x["_pts"]))
                top_g["unit_yen"] += 100
                remaining_units -= top_g["_pts"]
            else:
                break

    if remaining_units > 0:
        single_pts = [g for g in allocated if g["_pts"] == 1]
        if single_pts:
            top_single = max(single_pts, key=lambda x: x["_ev"])
            top_single["unit_yen"] += remaining_units * 100
            remaining_units = 0

    for g in allocated:
        g.pop("_pts", None)
        g.pop("_ev", None)
        g.pop("_weight", None)

    return allocated


def evaluate_and_build_1000yen_strategy(race_data, horse_features=None):
    horses = race_data["horses"]
    valid_horses = []
    used_nums = set()
    for idx, h in enumerate(horses, 1):
        n = h.get("num", idx)
        if not (1 <= n <= 18) or n in used_nums:
            for cand in range(1, 19):
                if cand not in used_nums:
                    n = cand
                    break
        h["num"] = n
        h["number"] = n
        h["umaban"] = n
        used_nums.add(n)
        valid_horses.append(h)
        if len(valid_horses) >= 18:
            break
    horses = valid_horses
    n_horses = len(horses)

    venue_base = race_data.get("venueBase", race_data.get("venue", "京都"))
    course_str = race_data.get("course", "芝1600m")
    is_dirt = "ダ" in course_str
    closer_bias, straight_type, course_profile_label = get_course_straight_profile(venue_base, course_str)

    front_cnt = sum(1 for h in horses if h.get("style") in ("逃げ", "先行"))
    front_ratio = front_cnt / max(1, n_horses)
    if front_ratio >= 0.42:
        pace_label = "差し有利ハイペース"
        pace_favor = {"逃げ": -1.3, "先行": -0.4, "差し": +1.7, "追込": +1.5}
    elif front_ratio <= 0.22:
        pace_label = "先行有利スローペース"
        pace_favor = {"逃げ": +1.6, "先行": +1.2, "差し": -0.3, "追込": -0.8}
    else:
        pace_label = "平均ミドルペース"
        pace_favor = {"逃げ": +0.2, "先行": +0.6, "差し": +0.9, "追込": +0.3}

    # コース直線長さによる有利不利をpace_favorに加味
    pace_favor["逃げ"] = round(pace_favor["逃げ"] - closer_bias * 0.65, 2)
    pace_favor["先行"] = round(pace_favor["先行"] - closer_bias * 0.35, 2)
    pace_favor["差し"] = round(pace_favor["差し"] + closer_bias * 0.75, 2)
    pace_favor["追込"] = round(pace_favor["追込"] + closer_bias * 0.90, 2)

    sorted_by_odds = sorted(horses, key=lambda x: x["odds"])
    for pop_idx, h in enumerate(sorted_by_odds, 1):
        h["popularity"] = pop_idx

    sim_stats, pace_pct = simulate_race_monte_carlo(race_data, n_trials=1000, horse_features=horse_features)
    sim_summary = f"展開試走1,000回(ハイ{pace_pct['high']}%/平均{pace_pct['middle']}%/スロー{pace_pct['slow']}%)"

    raw_scores = []
    for h in horses:
        style = h.get("style", "先行")
        waku = int(h.get("waku", 4))

        time_idx = calc_base_ability(h, horse_features=horse_features, straight_type=straight_type, is_dirt=is_dirt)
        pace_adj = pace_favor.get(style, 0.0)
        stretch_flow_adj = (float(h.get("stretchScore", 5.0)) - 5.0) * (0.55 if straight_type == "long" else 0.35)

        struct_score_adj = 0.0
        struct_win_mult = 1.0
        if waku in (1, 2) and style == "追込" and straight_type != "long":
            struct_win_mult = 0.91
            struct_score_adj = -1.5
        elif waku in (7, 8) and style == "逃げ":
            struct_win_mult = 0.89
            struct_score_adj = -1.8
        elif waku in (1, 2, 3, 4) and style in ("逃げ", "先行") and straight_type == "short":
            struct_win_mult = 1.06
            struct_score_adj = +1.1

        h["_structWinMult"] = struct_win_mult

        s_info = sim_stats.get(h["num"], {"winProb": 1.0 / max(1, n_horses), "placeProb": 3.0 / max(1, n_horses)})
        adj_win_prob = min(0.85, max(0.005, s_info["winProb"] * struct_win_mult))
        h["simWinRate"] = round(adj_win_prob * 100, 1)
        h["simPlaceRate"] = round(s_info["placeProb"] * 100, 1)

        sim_bonus = (s_info["placeProb"] - (3.0 / max(1, n_horses))) * 8.5
        total_score = time_idx + pace_adj * 0.65 + stretch_flow_adj + struct_score_adj + sim_bonus
        h["indexScore"] = time_idx
        h["speedScore"] = time_idx
        h["score"] = round(total_score, 1)
        h["totalScore"] = total_score
        raw_scores.append(total_score)

    mean_sc = sum(raw_scores) / len(raw_scores)
    raw_std = math.sqrt(sum((x - mean_sc) ** 2 for x in raw_scores) / max(1, len(raw_scores)))
    std_sc = max(raw_std, 2.5)

    exp_weights = []
    for h in horses:
        z = (h["totalScore"] - mean_sc) / std_sc
        h["zScore"] = round(50.0 + z * 10.0, 1)
        w = math.exp(z * 1.55) * h.get("_structWinMult", 1.0)
        h["_w"] = w
        exp_weights.append(w)

    sum_w = sum(exp_weights) or 1.0
    raw_est_probs = []
    for h in horses:
        base_prob = h["_w"] / sum_w
        sim_win_prob = sim_stats.get(h["num"], {}).get("winProb", base_prob) * h.get("_structWinMult", 1.0)
        est_p = base_prob * 0.45 + sim_win_prob * 0.55
        h["_rawEstProb"] = est_p
        raw_est_probs.append(est_p)

    sum_est = sum(raw_est_probs) or 1.0
    for h in horses:
        est_prob = min(0.80, max(0.005, h["_rawEstProb"] / sum_est))
        h["_estProb"] = est_prob
        eff_odds = min(h["odds"], 35.0 + math.sqrt(max(0.0, h["odds"] - 35.0)))
        raw_ev = est_prob * eff_odds * 0.80
        h["ev"] = round(min(1.65, max(0.60, raw_ev)), 2)

    is_high_pace_collapse = (front_cnt >= 4) and (pace_pct["high"] >= 35 or pace_label == "差し有利ハイペース")

    # 総合スコア順（無理な先行◎繰り上げは行わず、4角以降の勢い・コース適性・クラス格を素直に反映）
    ranked = sorted(horses, key=lambda x: x["totalScore"], reverse=True)

    # 過剰人気でEV極小の僅差1位のみ2位と入れ替え
    if len(ranked) >= 2 and ranked[0]["ev"] < 0.70 and (ranked[0]["totalScore"] - ranked[1]["totalScore"]) <= 1.2:
        if ranked[1]["ev"] >= 0.92 and ranked[1]["simPlaceRate"] >= 22.0:
            ranked[0], ranked[1] = ranked[1], ranked[0]

    honmei = ranked[0]
    taikou = ranked[1] if len(ranked) > 1 else ranked[0]
    tanana = ranked[2] if len(ranked) > 2 else taikou

    remaining = ranked[3:] if len(ranked) > 3 else []
    ana_candidates = [
        h for h in remaining
        if (float(h.get("videoBonus", 0.0)) >= 1.5 and h["odds"] >= 4.5)
        or (5.0 <= h["odds"] <= 65.0 and (h["ev"] >= 1.00 or float(h.get("stretchScore", 5.0)) >= 6.8))
    ]
    if ana_candidates:
        ana_candidates.sort(key=lambda x: (float(x.get("videoBonus", 0.0)) * 0.4 + x["ev"] + float(x.get("stretchScore", 5.0)) * 0.08), reverse=True)
    else:
        ana_candidates = sorted(remaining, key=lambda x: x["ev"], reverse=True)

    star_horse = ana_candidates[0] if ana_candidates else (ranked[3] if len(ranked) > 3 else tanana)
    himo_pool = [h for h in ranked[3:] if h["num"] != star_horse["num"]]

    by_index = sorted(horses, key=lambda x: x["indexScore"], reverse=True)
    top5_ability_nums = {x["num"] for x in by_index[:5]}

    danger_pop_lines = []
    danger_nums = set()
    safe_market_supported = []

    for h in sorted(himo_pool, key=lambda x: (x["popularity"], -x["totalScore"])):
        is_target_pop = (h["popularity"] in (2, 3)) or (2.5 <= h["odds"] <= 6.5)
        if not is_target_pop:
            continue

        reasons = []
        style = h.get("style", "先行")
        waku = int(h.get("waku", 4))
        st_sc = float(h.get("stretchScore", 5.0))
        last_margin = float(h["pastRuns"][0].get("margin", 0.0)) if h.get("pastRuns") else 0.0

        if straight_type == "short" and (not is_high_pace_collapse) and style == "追込":
            reasons.append("小回り直線短コースで追込脚質のため展開不利")
        if st_sc <= 3.8:
            reasons.append(f"4角以降の直線失速傾向(勢い{st_sc})")
        if waku in (1, 2) and style == "追込" and straight_type != "long":
            reasons.append("内枠の追込馬で直線詰まりリスク")
        elif waku in (7, 8) and style == "逃げ":
            reasons.append("外枠の逃げ馬でスタミナロス懸念")
        if h["num"] not in top5_ability_nums:
            if last_margin >= 0.6:
                reasons.append(f"前走着差{last_margin:.1f}秒かつ基礎能力上位5頭外(指数{h['indexScore']})")
            else:
                reasons.append(f"基礎能力スコア不足(指数{h['indexScore']})")
        if h["ev"] < 0.70:
            reasons.append(f"過剰人気で期待値大幅マイナス(EV:{h['ev']})")

        if reasons and float(h.get("videoBonus", 0.0)) < 1.5:
            danger_nums.add(h["num"])
            reason_txt = "・".join(reasons[:2])
            danger_pop_lines.append(
                f"【危険な人気馬】{h['num']}番{h['name']}({h['popularity']}番人気/{h['odds']}倍): {reason_txt}のため消し"
            )
        else:
            safe_market_supported.append(h)

    safe_market_nums = {h["num"] for h in safe_market_supported}
    other_safe_himos = [
        h for h in himo_pool
        if h["num"] not in danger_nums and h["num"] not in safe_market_nums
    ]
    himo_horses = (safe_market_supported + other_safe_himos)[:4]

    by_pace = sorted(
        horses,
        key=lambda x: (
            x.get("simPlaceRate", 0) * 0.4
            + pace_favor.get(x.get("style", ""), 0) * 2.0
            + float(x.get("stretchScore", 5.0)) * 0.9
            + x["indexScore"]
        ),
        reverse=True,
    )
    by_ana = sorted(horses, key=lambda x: x["ev"], reverse=True)

    for h in horses:
        n = h["num"]
        if n == honmei["num"]:
            m_jemi = "◎"
        elif n == taikou["num"]:
            m_jemi = "○"
        elif n == tanana["num"]:
            m_jemi = "▲"
        elif n == star_horse["num"]:
            m_jemi = "☆"
        elif any(n == x["num"] for x in himo_horses):
            m_jemi = "△"
        else:
            m_jemi = "-"

        if n == by_ana[0]["num"]:
            m_ana = "◎"
        elif len(by_ana) > 1 and n == by_ana[1]["num"]:
            m_ana = "☆"
        elif h["ev"] >= 1.05:
            m_ana = "▲"
        elif h["ev"] >= 0.96:
            m_ana = "△"
        else:
            m_ana = "-"

        if n == by_index[0]["num"]:
            m_idx = "◎"
        elif len(by_index) > 1 and n == by_index[1]["num"]:
            m_idx = "○"
        elif len(by_index) > 2 and n == by_index[2]["num"]:
            m_idx = "▲"
        elif h["indexScore"] >= 86.0:
            m_idx = "△"
        else:
            m_idx = "-"

        if n == by_pace[0]["num"]:
            m_pc = "◎"
        elif len(by_pace) > 1 and n == by_pace[1]["num"]:
            m_pc = "○"
        elif pace_favor.get(h.get("style", ""), 0) > 1.0:
            m_pc = "▲"
        elif h["indexScore"] >= 85.0:
            m_pc = "△"
        else:
            m_pc = "-"

        h["mark"] = m_jemi
        h["markJemi"] = m_jemi
        h["markAna"] = m_ana
        h["markSpeed"] = m_idx
        h["markPace"] = m_pc
        h["marks"] = {"jemi": m_jemi, "ana": m_ana, "index": m_idx, "pace": m_pc}

    h1, h2, h3, hs = honmei["num"], taikou["num"], tanana["num"], star_horse["num"]
    himo_nums = [x["num"] for x in himo_horses]
    horse_by_num = {h["num"]: h for h in horses}

    def _op(num):
        hh = horse_by_num.get(num, honmei)
        return float(hh["odds"]), float(hh.get("_estProb", 0.05))

    def _combo_quinella(na, nb):
        oa, pa = _op(na)
        ob, pb = _op(nb)
        return max(1.5, oa * ob * 0.35), min(0.65, max(0.005, (pa * pb) * 2.2))

    def _combo_exacta(na, nb):
        oa, pa = _op(na)
        ob, pb = _op(nb)
        return max(2.0, oa * ob * 0.65), min(0.55, max(0.004, (pa * pb) * 1.3))

    def _combo_wide(na, nb):
        oa, pa = _op(na)
        ob, pb = _op(nb)
        return max(1.2, oa * ob * 0.14), min(0.75, max(0.015, (pa * pb) * 4.5))

    def _combo_trio(na, nb, nc):
        oa, pa = _op(na)
        ob, pb = _op(nb)
        oc, pc = _op(nc)
        return max(3.0, oa * ob * oc * 0.12), min(0.45, max(0.003, (pa * pb * pc) * 12.0))

    def _uniq(seq):
        out = []
        for x in seq:
            if x not in out:
                out.append(x)
        return out

    def _trio_form_combos(col1, col2, col3):
        seen = set()
        combos = []
        for a in col1:
            for b in col2:
                for c in col3:
                    if len({a, b, c}) == 3:
                        key = tuple(sorted([a, b, c]))
                        if key not in seen:
                            seen.add(key)
                            combos.append(_combo_trio(key[0], key[1], key[2]))
        return combos

    def _trio_1axis_combos(axis, opps):
        seen = set()
        combos = []
        for i in range(len(opps)):
            for j in range(i + 1, len(opps)):
                a, b, c = axis, opps[i], opps[j]
                if len({a, b, c}) == 3:
                    key = tuple(sorted([a, b, c]))
                    if key not in seen:
                        seen.add(key)
                        combos.append(_combo_trio(key[0], key[1], key[2]))
        return combos

    def _make_group(name, combos):
        pts = max(1, len(combos))
        inv_sum = sum(1.0 / max(c[0], 1.01) for c in combos)
        syn_odds = round(1.0 / inv_sum, 2) if inv_sum > 0 else 2.0
        syn_prob = round(min(0.85, sum(c[1] for c in combos)), 4)
        return {
            "name": name,
            "pts": pts,
            "est_odds": syn_odds,
            "est_prob": syn_prob,
        }

    safe_fallback_nums = [x["num"] for x in ranked if x["num"] != h1 and x["num"] not in danger_nums]
    all_fallback_nums = [x["num"] for x in ranked if x["num"] != h1]
    opps_ordered = _uniq([x for x in ([h2, h3] + himo_nums + [hs] + safe_fallback_nums) if x != h1 and x not in danger_nums])
    if len(opps_ordered) < 4:
        opps_ordered = _uniq(opps_ordered + all_fallback_nums)

    h4 = himo_nums[0] if len(himo_nums) >= 1 else (opps_ordered[2] if len(opps_ordered) > 2 else hs)
    h5 = himo_nums[1] if len(himo_nums) >= 2 else (opps_ordered[3] if len(opps_ordered) > 3 else hs)

    ability_gap = honmei["indexScore"] - taikou["indexScore"]
    z_gap_1_2 = honmei["zScore"] - taikou["zScore"]
    o1, p1 = _op(h1)

    is_dominant_1strong = (
        (ability_gap >= 3.5 or z_gap_1_2 >= 3.5 or (o1 <= 3.5 and honmei["simWinRate"] >= 22.0))
        and o1 <= 4.8
    )
    is_upset_race = (
        o1 >= 7.0
        or (o1 >= 5.5 and star_horse["ev"] >= 1.15)
        or (is_high_pace_collapse and o1 >= 4.5)
    )

    conf_rank, conf_score = calc_honest_confidence(horses, ranked, pace_pct, is_upset_race)

    is_extra_buy = (conf_rank == "S" and conf_score >= 90)
    extra_buy_reason = ""
    if is_extra_buy:
        extra_buy_reason = (
            f"🔥【追加購入推奨・ジェミ特選】信頼度S({conf_score}点)の絶対的自信レース！"
            f"◎{h1}番{honmei['name']}の試走3着内率({honmei['simPlaceRate']}%)・"
            f"能力指数({honmei['indexScore']})・4角以降の勢い({honmei.get('stretchTag', '')})が抜けており、"
            f"通常予算(1,000円)に加えての追加購入をおすすめします。"
        )

    h1_stretch = honmei.get("stretchTag", "直線標準")
    bet_groups = []
    if is_dominant_1strong:
        strategy_name = "1強・頭固定型"
        exacta_opps = _uniq([x for x in [h2, h3] if x != h1])[:2]
        axis_opps = _uniq([x for x in [h2, h3, h4, hs] + opps_ordered if x != h1])[:4]
        trio_combos = _trio_1axis_combos(h1, axis_opps)
        bet_groups = [
            _make_group(
                f"【馬単本線】{h1} → {','.join(str(x) for x in exacta_opps)}",
                [_combo_exacta(h1, x) for x in exacta_opps],
            ),
            _make_group(
                f"【三連複1頭軸】{h1} - {','.join(str(x) for x in axis_opps)}",
                trio_combos or [_combo_trio(h1, h2, h3)],
            ),
        ]
        comment = (
            f"舞台は【{course_profile_label} / {pace_label} / {sim_summary}】。"
            f"能力指数{honmei['indexScore']}・{h1_stretch}の◎{h1}番{honmei['name']}({honmei['style']})が1強。"
            f"【馬単本線】へ厚く傾斜配分しつつ、厳選相手4頭への【三連複1頭軸({len(trio_combos)}点)】でヒモ抜けを防ぐ構成。"
        )
    elif is_upset_race:
        strategy_name = "波乱・穴狙い型"
        wide_o, wide_p = _combo_wide(h1, hs)
        if wide_o >= 4.0 and hs != h1:
            punch_group = _make_group(f"【ワイド穴】{h1} - {hs}", [(wide_o, wide_p)])
            punch_desc = f"想定オッズ{wide_o:.1f}倍の【ワイド穴】{h1}-{hs}"
        else:
            punch_group = _make_group(f"【単勝穴】{h1}", [(max(1.5, o1), p1)])
            punch_desc = f"期待値EV:{honmei['ev']}の【単勝穴】{h1}番"

        col2 = _uniq([x for x in [h2, hs] if x != h1])[:2]
        if len(col2) < 2:
            col2 = _uniq([x for x in [h2, h3, hs] if x != h1])[:2]
        col3 = _uniq([x for x in col2 + [h3, h4, h5] + opps_ordered if x != h1])[:5]
        trio_combos = _trio_form_combos([h1], col2, col3)

        bet_groups = [
            punch_group,
            _make_group(
                f"【三連複F】{h1} ✕ {','.join(str(x) for x in col2)} ✕ {','.join(str(x) for x in col3)}",
                trio_combos or [_combo_trio(h1, h2, h3)],
            ),
        ]
        comment = (
            f"舞台は【{course_profile_label} / {pace_label} / {sim_summary}】。"
            f"波乱含みの一戦で、4角以降の勢い({h1_stretch})と期待値を兼ね備えた◎{h1}番{honmei['name']}({honmei['style']})から勝負。"
            f"{punch_desc}に厚く張りつつ、穴馬☆{hs}番を2列目に抜擢した【三連複F({len(trio_combos)}点)】で高配当を射抜く。"
        )
    else:
        strategy_name = "堅実・中配当型"
        col2 = _uniq([x for x in [h2, h3] if x != h1])[:2]
        col3_target = 4 if n_horses <= 9 else 5
        col3 = _uniq([x for x in col2 + [h4, hs, h5] + opps_ordered if x != h1])[:col3_target]
        trio_combos = _trio_form_combos([h1], col2, col3)

        bet_groups = [
            _make_group(f"【馬連本線】{h1} - {h2}", [_combo_quinella(h1, h2)]),
            _make_group(f"【馬連対抗】{h1} - {h3}", [_combo_quinella(h1, h3)]),
            _make_group(
                f"【三連複F】{h1} ✕ {','.join(str(x) for x in col2)} ✕ {','.join(str(x) for x in col3)}",
                trio_combos or [_combo_trio(h1, h2, h3)],
            ),
        ]
        comment = (
            f"舞台は【{course_profile_label} / {pace_label} / {sim_summary}】。"
            f"4角以降の勢い({h1_stretch})と試走3着内率{honmei['simPlaceRate']}%が光る◎{h1}番{honmei['name']}({honmei['style']})が軸。"
            f"【馬連本線・対抗】へダッチング＆ケリー傾斜配分しつつ、実力上位馬と穴☆を押さえた【三連複F({len(trio_combos)}点)】で確実な回収を狙う。"
        )

    if conf_score < 35:
        comment += f"（※上位の能力差が極めて小さい大混戦・信頼度{conf_score}点のため、無理な厚張りは禁物）"

    video_notes = []
    for fh in [honmei, taikou, tanana, star_horse]:
        vb = float(fh.get("videoBonus", 0.0))
        vm = str(fh.get("videoMemo", "")).strip()
        if vb >= 1.5 or vm:
            tag_memo = vm or "前走不利・距離ロスによる巻き返し期待"
            video_notes.append(f"【動画・定性特注】{fh['num']}番{fh['name']}({fh['markJemi']} / 能力+{vb:.1f}点): {tag_memo}")

    if video_notes:
        comment = comment + "\n" + "\n".join(video_notes)
    if danger_pop_lines:
        comment = comment + "\n" + "\n".join(danger_pop_lines)

    allocated_groups = allocate_dutching_kelly(bet_groups, total_budget=1000)

    buy_parts = []
    total_pts = 0
    total_yen = 0
    for g in allocated_groups:
        u_yen = int(g.get("unit_yen", 0))
        pts = int(g.get("pts", 1))
        if u_yen <= 0 or pts <= 0:
            continue
        buy_parts.append(f"{g['name']} ({pts}点/{u_yen}円)")
        total_pts += pts
        total_yen += pts * u_yen

    ai_buy = " / ".join(buy_parts) + f" [計{total_pts}点/{total_yen:,}円]" if buy_parts else f"【単勝本線】{h1} (1点/1000円)"
    strategy_tag = f"{strategy_name} (計{total_yen:,}円)"

    for h in horses:
        h.pop("_w", None)
        h.pop("_estProb", None)
        h.pop("_rawEstProb", None)
        h.pop("_structWinMult", None)

    clean_v = re.sub(r"[（\(].*?[）\)]", "", race_data.get("venue", "")).strip()
    race_data["venue"] = clean_v or race_data.get("venueBase", "京都")

    r_num_val = int(race_data.get("rNum", 0) or 0)
    race_data["horses"] = sorted(horses, key=lambda x: x["num"])
    race_data["strategyName"] = strategy_name
    race_data["strategyTag"] = strategy_tag
    race_data["confidence"] = conf_rank
    race_data["confidenceScore"] = conf_score
    race_data["isBuyTarget"] = is_buy_target_race(r_num_val, conf_score)
    race_data["isEarlyPick"] = (r_num_val <= 8 and conf_score >= MIN_BUY_SCORE_EARLY)
    race_data["extraBuyRecommended"] = is_extra_buy
    race_data["extraBuyReason"] = extra_buy_reason
    race_data["videoNotes"] = video_notes
    race_data["dangerPop"] = danger_pop_lines
    race_data["dangerPopText"] = " / ".join(danger_pop_lines)
    race_data["aiSummary"] = comment
    race_data["aiComment"] = comment
    race_data["aiBuy"] = ai_buy
    race_data["budget"] = total_yen or 1000
    race_data["topPicks"] = [honmei, taikou, tanana]
    return race_data


def build_win5_prediction(races, all_win5_sets=None, jra_win5_targets=None):
    for r in races:
        r["isWin5"] = False

    race_map = {r.get("raceId"): r for r in races}
    vr_map = {(r.get("venue"), r.get("rNum")): r for r in races}
    win5_races = []

    if jra_win5_targets and len(jra_win5_targets) == 5:
        matched = [vr_map[t] for t in jra_win5_targets if t in vr_map]
        if len(matched) == 5:
            win5_races = matched

    if not win5_races and all_win5_sets:
        for w5_rids in all_win5_sets:
            matched = [race_map[rid] for rid in w5_rids if rid in race_map]
            if len(matched) == 5:
                win5_races = matched
                break

    if not win5_races:
        cands = [r for r in races if r.get("rNum") in (7, 8, 9, 10, 11, 12)]
        cands.sort(key=lambda x: (x.get("startTime", "15:00"), x.get("rNum", 10)))
        win5_races = cands[-5:] if len(cands) >= 5 else sorted(races, key=lambda x: x.get("startTime", "15:00"))[-5:]

    for wr in win5_races:
        wr["isWin5"] = True

    legs = []
    lines_text = []
    total_combos = 1
    pick_counts = [2, 2, 2, 1, 1]

    for idx, r in enumerate(win5_races):
        cnt = pick_counts[idx] if idx < len(pick_counts) else 1
        picks = r.get("topPicks", [])[:cnt]
        if not picks and r.get("horses"):
            mark_order = {"◎": 1, "○": 2, "▲": 3, "☆": 4, "△": 5}
            picks = sorted(r["horses"], key=lambda x: (mark_order.get(x.get("mark"), 9), -x.get("totalScore", 0)))[:cnt]

        total_combos *= max(1, len(picks))

        v_name = r.get("venue", "")
        r_num = r.get("rNum", 11)
        s_name = r.get("shortRaceName", r.get("raceName", ""))
        picks_str = ", ".join([f"{p['num']}番 {p['name']}" for p in picks])
        lines_text.append(f"第{idx+1}戦 [{v_name} {r_num}R {s_name}]: {picks_str}")

        h_objs = [
            {
                "num": p["num"],
                "number": p["num"],
                "umaban": p["num"],
                "name": p["name"],
                "horseName": p["name"],
                "odds": p["odds"],
                "ev": p.get("ev", 1.0),
                "mark": p.get("mark", "◎")
            }
            for p in picks
        ]

        legs.append({
            "leg": idx + 1,
            "step": idx + 1,
            "raceNumber": r_num,
            "venue": v_name,
            "rNum": r_num,
            "raceName": f"{v_name} {r_num}R {s_name}",
            "shortRaceName": s_name,
            "startTime": r.get("startTime", "15:00"),
            "horseNums": [p["num"] for p in picks],
            "numbers": [p["num"] for p in picks],
            "selectedHorses": h_objs,
            "picks": h_objs,
            "horses": h_objs,
            "picksText": picks_str
        })

    summary_title = f"【AI厳選WIN5戦略】計{total_combos}点 (不利なし突出1頭固定×2戦 + 2頭押さえ×3戦) / 予算{total_combos*100}円"
    concept_str = "コース直線適性・4角以降の勢い・前走クラス格を重視し、過剰人気馬を除外して高配当を射抜く。"

    return {
        "title": summary_title,
        "summary": summary_title,
        "text": "\n".join([summary_title] + lines_text + [f"狙い: {concept_str}"]),
        "lines": lines_text,
        "totalCombinations": total_combos,
        "points": total_combos,
        "unitYen": 100,
        "estimatedCost": total_combos * 100,
        "budget": total_combos * 100,
        "concept": concept_str,
        "races": legs,
        "legs": legs
    }


def main():
    print("🚀 ジェミ予想 AI Predictor 完全版データ生成（直線勢い評価＋コース直線補正＋クラス格補正）を開始します...")
    stats_obj = build_complete_stats()
    horse_features = load_horse_features()

    jra_win5_by_md = fetch_jra_official_win5_schedule()
    all_win5_sets = fetch_all_official_win5_sets()
    print(f"  -> netkeiba WIN5補助セット取得数: {len(all_win5_sets)}日分")

    day_groups = discover_all_target_days(jra_win5_by_md=jra_win5_by_md)
    schedule_days = []

    venue_order = {"東京": 1, "中山": 2, "京都": 3, "阪神": 4, "新潟": 5, "中京": 6, "福島": 7, "小倉": 8, "札幌": 9, "函館": 10}

    for d_str, rids in day_groups:
        dt_obj = datetime.datetime.strptime(d_str, "%Y%m%d")
        t_date_disp = f"{dt_obj.year}年{dt_obj.month}月{dt_obj.day}日"
        day_label = f"{dt_obj.month}/{dt_obj.day}({WEEKDAY_JP[dt_obj.weekday()]})"
        all_day_races = []

        print(f"=== {t_date_disp} (全{len(rids)}レース) の解析 ===")
        for rid in rids:
            r_info = parse_shutuba_page(rid)
            if not r_info:
                continue
            r_info = evaluate_and_build_1000yen_strategy(r_info, horse_features=horse_features)
            all_day_races.append(r_info)
            time.sleep(0.15)

        if all_day_races:
            md_key = (dt_obj.month, dt_obj.day)
            jra_targets = jra_win5_by_md.get(md_key)
            day_win5 = build_win5_prediction(all_day_races, all_win5_sets, jra_win5_targets=jra_targets)

            # 9〜12Rは全表示、1〜8RはSランク（90点以上）のみ表示
            display_day_races = [
                r for r in all_day_races
                if (r.get("rNum", 0) in (9, 10, 11, 12))
                or (r.get("rNum", 0) <= 8 and r.get("confidenceScore", 0) >= MIN_BUY_SCORE_EARLY)
            ]
            display_day_races.sort(key=lambda x: (venue_order.get(x.get("venue"), 99), x.get("rNum", 99)))

            buy_target_cnt = sum(1 for r in display_day_races if r.get("isBuyTarget"))
            b_plus_cnt = sum(1 for r in display_day_races if r.get("confidenceScore", 0) >= 55)
            early_s_cnt = sum(1 for r in display_day_races if r.get("isEarlyPick"))

            for r in all_day_races:
                if "topPicks" in r:
                    del r["topPicks"]

            print(f"  -> {t_date_disp}: 全{len(all_day_races)}R解析 → 表示{len(display_day_races)}R (購入対象 {buy_target_cnt}R / うち1〜8R特選S {early_s_cnt}R)")

            schedule_days.append({
                "date": d_str,
                "label": day_label,
                "targetDate": t_date_disp,
                "analyzedCount": len(all_day_races),
                "displayCount": len(display_day_races),
                "aPlusCount": buy_target_cnt,
                "buyTargetCount": buy_target_cnt,
                "bPlusCount": b_plus_cnt,
                "earlyPickCount": early_s_cnt,
                "minConfidenceScoreLate": MIN_BUY_SCORE_LATE,
                "minConfidenceScoreEarly": MIN_BUY_SCORE_EARLY,
                "races": display_day_races,
                "win5": day_win5,
                "win5Strategy": day_win5.get("text", "")
            })

    if schedule_days:
        save_predictions_archive(schedule_days)
        primary_day = schedule_days[0]
        target_date_display = primary_day["targetDate"]
        races_out = primary_day["races"]
        win5_data = primary_day["win5"]
        analyzed_out = primary_day.get("analyzedCount", len(races_out))
        buy_target_out = primary_day.get("buyTargetCount", 0)
        b_plus_out = primary_day.get("bPlusCount", 0)
    else:
        print("⚠️ 今回レース取得が0件でした（netkeibaメンテナンス等の可能性）。直前の有効データを復元します。")
        prev_valid = restore_last_valid_today_from_git()
        if prev_valid:
            target_date_display = prev_valid.get("targetDate", datetime.datetime.now(JST).strftime("%Y年%m月%d日"))
            races_out = prev_valid.get("races", [])
            win5_data = prev_valid.get("win5", {})
            schedule_days = prev_valid.get("scheduleDays", [])
            analyzed_out = prev_valid.get("analyzedCount", len(races_out))
            buy_target_out = prev_valid.get("buyTargetCount", 0)
            b_plus_out = prev_valid.get("bPlusCount", 0)
        else:
            target_date_display = datetime.datetime.now(JST).strftime("%Y年%m月%d日")
            races_out = []
            win5_data = {}
            analyzed_out = 0
            buy_target_out = 0
            b_plus_out = 0

    now_str = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    final_json = {
        "targetDate": target_date_display,
        "updatedAt": now_str,
        "budgetPerRace": 1000,
        "totalBudget": buy_target_out * 1000,
        "analyzedCount": analyzed_out,
        "displayCount": len(races_out),
        "aPlusCount": buy_target_out,
        "buyTargetCount": buy_target_out,
        "bPlusCount": b_plus_out,
        "minConfidenceScoreLate": MIN_BUY_SCORE_LATE,
        "minConfidenceScoreEarly": MIN_BUY_SCORE_EARLY,
        "stats": stats_obj,
        "hitRate": stats_obj["hitRate"],
        "recoveryRate": stats_obj["recoveryRate"],
        "roi": stats_obj["roi"],
        "totalBets": stats_obj["totalBets"],
        "totalRaces": stats_obj["totalRaces"],
        "hitCount": stats_obj["hitCount"],
        "bPlusStats": stats_obj.get("bPlusStats", _default_tier_stats()),
        "aPlusStats": stats_obj.get("aPlusStats", _default_tier_stats()),
        "sStats": stats_obj.get("sStats", _default_tier_stats()),
        "markStats": stats_obj["markStats"],
        "markStatsList": stats_obj["markStatsList"],
        "hitDetails": stats_obj["hitDetails"],
        "allBetRaces": stats_obj["allBetRaces"],
        "history": stats_obj["hitDetails"],
        "results": stats_obj["allBetRaces"],
        "win5": win5_data,
        "win5Strategy": win5_data.get("text", ""),
        "races": races_out,
        "scheduleDays": schedule_days
    }

    os.makedirs("data", exist_ok=True)
    for path in ("data/today.json", "today.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(final_json, f, ensure_ascii=False, indent=2)

    print(f"✅ 完了！ {len(schedule_days)}日分 / 表示{len(races_out)}レース（うち購入対象 {buy_target_out}レース）を出力しました。")


if __name__ == "__main__":
    main()
