import os
import re
import json
import time
import subprocess
import datetime
from itertools import combinations
from bs4 import BeautifulSoup
import requests

JST = datetime.timezone(datetime.timedelta(hours=9))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

STATS_PATHS = ("data/stats.json", "stats.json")
TODAY_PATHS = ("data/today.json", "today.json")
ARCHIVE_PATH = "data/predictions_archive.json"

# 信頼度ランク別の判定しきい値
MIN_B_PLUS_SCORE = 55   # B以上（S/A/Bランク）
MIN_A_PLUS_SCORE = 75   # A以上（S/Aランク）
MIN_S_SCORE = 90        # Sランクのみ


def fetch_html(url, default_enc="euc-jp", retries=3):
    for i in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            raw = res.content
            if b"utf-8" in raw[:1000].lower() or b"utf8" in raw[:1000].lower():
                return raw.decode("utf-8", errors="replace")
            for enc in (default_enc, "euc_jp", "cp932", "utf-8"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode(default_enc, errors="replace")
        except Exception as e:
            print(f"  [retry {i+1}/{retries}] {url}: {e}")
            time.sleep(1.2)
    return ""


def parse_nums(s):
    return [int(x) for x in re.findall(r"\d+", str(s)) if 1 <= int(x) <= 18]


def expand_ai_buy(ai_buy_str):
    """aiBuy文字列を (券種, 組番セットリスト, 1点金額) に展開する"""
    if not ai_buy_str:
        return []
    main_p = re.sub(r"\[[^\]]*計\d+点[^\]]*\]", "", str(ai_buy_str).split("★")[0]).strip()
    tickets = []

    for seg in [s.strip() for s in main_p.split("/") if s.strip()]:
        m_pt = re.search(r"(\d+)\s*点\s*/\s*(?:各)?\s*(\d+)\s*円", seg)
        unit_yen = int(m_pt.group(2)) if m_pt else 100
        unit_yen = max(100, (unit_yen // 100) * 100)

        m_lb = re.search(r"【([^】]+)】([^\(（]+)", seg)
        if not m_lb:
            continue
        label, body = m_lb.group(1).strip(), m_lb.group(2).strip()

        combos = []
        btype = ""
        if "単勝" in label:
            btype = "単勝"
            ns = parse_nums(body)
            if ns:
                combos = [(ns[0],)]
        elif "馬単" in label:
            btype = "馬単"
            tp = re.split(r"→|->|-", body)
            if len(tp) >= 2:
                h1, h2 = parse_nums(tp[0]), parse_nums(tp[1])
                combos = [(a, b) for a in h1 for b in h2 if a != b]
        elif "三連複F" in label:
            btype = "3連複"
            fp = re.split(r"[✕×xX\-]", body)
            if len(fp) >= 3:
                h1, h2, h3 = parse_nums(fp[0]), parse_nums(fp[1]), parse_nums(fp[2])
                seen = set()
                for a in h1:
                    for b in h2:
                        for c in h3:
                            if len({a, b, c}) == 3:
                                k = tuple(sorted([a, b, c]))
                                if k not in seen:
                                    seen.add(k)
                                    combos.append(k)
        elif "三連複1頭軸" in label:
            btype = "3連複"
            bp = body.split("-", 1)
            if len(bp) == 2:
                ax, opps = parse_nums(bp[0]), parse_nums(bp[1])
                if ax:
                    combos = [tuple(sorted([ax[0], a, b])) for a, b in combinations(opps, 2) if len({ax[0], a, b}) == 3]
        elif "三連複2頭軸" in label:
            btype = "3連複"
            bp = body.split("-", 1)
            if len(bp) == 2:
                ax, opps = parse_nums(bp[0]), parse_nums(bp[1])
                if len(ax) >= 2:
                    combos = [tuple(sorted([ax[0], ax[1], c])) for c in opps if len({ax[0], ax[1], c}) == 3]
        elif "三連複BOX" in label:
            btype = "3連複"
            ns = parse_nums(body)
            combos = [tuple(sorted(c)) for c in combinations(ns, 3)]
        elif "BOX" in label and ("馬連" in label or "ワイド" in label):
            btype = "馬連" if "馬連" in label else "ワイド"
            ns = parse_nums(body)
            combos = [tuple(sorted(c)) for c in combinations(ns, 2)]
        elif "馬連" in label or "ワイド" in label:
            btype = "馬連" if "馬連" in label else "ワイド"
            if "-" in body:
                bp = body.split("-", 1)
                h1, h2 = parse_nums(bp[0]), parse_nums(bp[1])
                combos = [tuple(sorted([a, b])) for a in h1 for b in h2 if a != b]

        if btype and combos:
            tickets.append({"type": btype, "combos": combos, "unit_yen": unit_yen})

    return tickets


def fetch_race_result_and_payout(race_id):
    """netkeibaの確定結果ページから1〜3着馬番と確定払戻金を取得する"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    html = fetch_html(url, default_enc="euc_jp")
    if not html or "RaceTable01" not in html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    top3 = []
    for tr in soup.select("table.RaceTable01 tbody tr, table.RaceTable01 tr.HorseList"):
        tds = tr.select("td")
        if len(tds) < 4:
            continue
        rk_txt = tds[0].get_text(strip=True)
        uma_txt = tds[2].get_text(strip=True)
        if rk_txt.isdigit() and uma_txt.isdigit():
            rk = int(rk_txt)
            if 1 <= rk <= 3:
                top3.append(int(uma_txt))

    if len(top3) < 3:
        return None

    payouts = {}
    for tr in soup.select("table.Payout_Detail_Table tr, table.Pay_Table_01 tr"):
        th = tr.select_one("th")
        if not th:
            continue
        btype = re.sub(r"\s+", "", th.get_text(strip=True)).replace("３", "3")
        tds = tr.select("td")
        if len(tds) < 2:
            continue

        res_txt = tds[0].get_text(" ", strip=True)
        pay_txt = tds[1].get_text(" ", strip=True)
        pay_vals = [int(p.replace(",", "")) for p in re.findall(r"([0-9,]+)円", pay_txt)]
        if not pay_vals:
            continue

        nums = [int(x) for x in re.findall(r"\d+", res_txt) if 1 <= int(x) <= 18]
        n_per_combo = 3 if "3連" in btype else (2 if ("連" in btype or "ワイド" in btype or "馬単" in btype) else 1)

        payouts.setdefault(btype, {})
        for idx, pay_yen in enumerate(pay_vals):
            chunk = nums[idx * n_per_combo:(idx + 1) * n_per_combo]
            if len(chunk) == n_per_combo:
                key = tuple(chunk) if btype in ("馬単", "3連単") else tuple(sorted(chunk))
                payouts[btype][key] = pay_yen

    if not payouts:
        return None

    return {"top3": set(top3), "payouts": payouts}


def load_json(paths, default=None):
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return default if default is not None else {}


def _extract_races_from_today_obj(today_obj, candidates):
    if not isinstance(today_obj, dict):
        return
    for day in today_obj.get("scheduleDays", []):
        d_str = str(day.get("date", ""))
        d_iso = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}" if len(d_str) == 8 else ""
        for r in day.get("races", []):
            rid = str(r.get("raceId", ""))
            if rid and rid not in candidates:
                rc = dict(r)
                if d_iso and not rc.get("raceDate"):
                    rc["raceDate"] = d_iso
                candidates[rid] = rc
    for r in today_obj.get("races", []):
        rid = str(r.get("raceId", ""))
        if rid and rid not in candidates:
            candidates[rid] = dict(r)


def collect_candidate_races():
    """アーカイブ・現在のtoday.json・Git過去コミットのtoday.jsonから未集計の候補レースを集める"""
    candidates = {}

    archive = load_json([ARCHIVE_PATH], default=[])
    if isinstance(archive, list):
        for r in archive:
            if isinstance(r, dict) and r.get("raceId"):
                candidates[str(r["raceId"])] = r

    today = load_json(TODAY_PATHS, default={})
    _extract_races_from_today_obj(today, candidates)

    try:
        commits = subprocess.check_output(
            ["git", "log", "--format=%H", "-n", "40", "--", "data/today.json"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip().splitlines()
        for sha in commits:
            try:
                raw = subprocess.check_output(
                    ["git", "show", f"{sha}:data/today.json"],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
                _extract_races_from_today_obj(json.loads(raw), candidates)
            except Exception:
                continue
    except Exception:
        pass

    return candidates


def _init_tier_counter(stats_obj, key):
    src = stats_obj.get(key) if isinstance(stats_obj.get(key), dict) else {}
    return {
        "totalBets": int(src.get("totalBets") or 0),
        "hitCount": int(src.get("hitCount") or 0),
        "totalInvestment": int(src.get("totalInvestment") or 0),
        "totalReturn": int(src.get("totalReturn") or 0),
    }


def _add_tier_result(counter, cost, payout):
    counter["totalBets"] += 1
    counter["totalInvestment"] += cost
    counter["totalReturn"] += payout
    if payout > 0:
        counter["hitCount"] += 1


def _finalize_tier_stats(counter):
    bets = counter["totalBets"]
    hits = counter["hitCount"]
    inv = counter["totalInvestment"]
    ret = counter["totalReturn"]
    return {
        "totalBets": bets,
        "hitCount": hits,
        "hitRate": round(hits * 100.0 / bets, 1) if bets > 0 else None,
        "recoveryRate": round(ret * 100.0 / max(1, inv), 1) if bets > 0 else None,
        "totalInvestment": inv,
        "totalReturn": ret,
    }


def _fmt_tier_log(label, t):
    if t["totalBets"] <= 0:
        return f"{label}: --% (0/0)"
    return f"{label}: 的中率 {t['hitRate']}% ({t['hitCount']}/{t['totalBets']})・回収率 {t['recoveryRate']}%"


def main():
    stats = load_json(STATS_PATHS, default={})
    if not isinstance(stats, dict):
        stats = {}

    evaluated_ids = set(str(x) for x in stats.get("evaluatedRaceIds", []))
    candidates = collect_candidate_races()
    print(f"🔎 候補レース数: {len(candidates)}件（うち集計済み: {len(evaluated_ids)}件）")

    now_str = datetime.datetime.now(JST).strftime("%Y-%m-%d")

    total_bets = int(stats.get("totalBets") or 91)
    hit_count = int(stats.get("hitCount") or 33)
    total_inv = int(stats.get("totalInvestment") or (total_bets * 1000))
    total_ret = int(stats.get("totalReturn") or int(total_inv * float(stats.get("recoveryRate") or 290.2) / 100))

    # 信頼度ランク別の実績カウンター（B以上 / A以上 / S）
    b_plus_cnt = _init_tier_counter(stats, "bPlusStats")
    a_plus_cnt = _init_tier_counter(stats, "aPlusStats")
    s_only_cnt = _init_tier_counter(stats, "sStats")

    hit_details = list(stats.get("hitDetails") or [])
    all_bet_races = list(stats.get("allBetRaces") or [])

    mark_list = stats.get("markStatsList") or []
    mark_counts = {}
    for sym, eng, jp, full_lbl, def_h, def_t in [
        ("◎", "honmei", "本命", "◎ 本命", 59, 91),
        ("○", "taikou", "対抗", "○ 対抗", 47, 91),
        ("▲", "tanana", "単穴", "▲ 単穴", 38, 91),
        ("☆", "ana", "穴", "☆ 穴", 26, 91),
        ("△", "renka", "連下", "△ 連下", 22, 91),
    ]:
        src = {}
        if isinstance(stats.get("markStats"), dict):
            src = stats["markStats"].get(sym) or {}
        elif isinstance(mark_list, list):
            src = next((m for m in mark_list if m.get("mark") == sym), {})
        mark_counts[sym] = {
            "eng": eng, "jp": jp, "full": full_lbl,
            "hit": int(src.get("hit") or def_h),
            "total": int(src.get("total") or def_t),
        }

    new_count = 0
    for rid, race in sorted(candidates.items()):
        if rid in evaluated_ids:
            continue
        r_date = str(race.get("raceDate") or f"{rid[:4]}-{now_str[5:7]}-{now_str[8:10]}")
        res = fetch_race_result_and_payout(rid)
        if not res:
            continue

        top3_set = res["top3"]
        payouts = res["payouts"]
        tickets = expand_ai_buy(race.get("aiBuy", ""))
        if not tickets:
            continue

        race_cost = sum(len(t["combos"]) * t["unit_yen"] for t in tickets)
        race_payout = 0
        hit_types = []
        for t in tickets:
            pay_map = payouts.get(t["type"], {})
            for cb in t["combos"]:
                if cb in pay_map:
                    race_payout += pay_map[cb] * (t["unit_yen"] // 100)
                    if t["type"] not in hit_types:
                        hit_types.append(t["type"])

        # 全体実績へ加算
        total_bets += 1
        total_inv += race_cost
        total_ret += race_payout
        if race_payout > 0:
            hit_count += 1

        # 信頼度ランク別実績へ加算（B以上 / A以上 / S）
        conf_score = int(race.get("confidenceScore") or 0)
        conf_rank = str(race.get("confidence") or "").strip().upper()
        is_s = (conf_score >= MIN_S_SCORE) or (conf_rank == "S")
        is_a_plus = (conf_score >= MIN_A_PLUS_SCORE) or (conf_rank in ("S", "A"))
        is_b_plus = (conf_score >= MIN_B_PLUS_SCORE) or (conf_rank in ("S", "A", "B"))

        if is_b_plus:
            _add_tier_result(b_plus_cnt, race_cost, race_payout)
        if is_a_plus:
            _add_tier_result(a_plus_cnt, race_cost, race_payout)
        if is_s:
            _add_tier_result(s_only_cnt, race_cost, race_payout)

        for h in race.get("horses", []):
            mk = str(h.get("markJemi") or h.get("mark") or "-")
            if mk in mark_counts:
                mark_counts[mk]["total"] += 1
                if int(h.get("num", 0)) in top3_set:
                    mark_counts[mk]["hit"] += 1

        venue = race.get("venue", "")
        r_num = race.get("rNum", "")
        r_name = race.get("shortRaceName") or race.get("raceName") or f"{r_num}R"
        rec_entry = {
            "raceId": rid,
            "date": r_date,
            "venue": f"{venue}{r_num}R",
            "race": f"{venue}{r_num}R {r_name}",
            "raceName": r_name,
            "confidence": conf_rank,
            "confidenceScore": conf_score,
            "isBPlus": is_b_plus,
            "isAPlus": is_a_plus,
            "isS": is_s,
            "betType": "・".join(hit_types) if hit_types else "予想",
            "result": "的中" if race_payout > 0 else "不的中",
            "invest": race_cost,
            "cost": race_cost,
            "payout": race_payout,
            "return": race_payout,
            "roi": round(race_payout * 100 / max(1, race_cost)),
        }
        all_bet_races.insert(0, rec_entry)
        if race_payout > 0:
            hit_details.insert(0, rec_entry)

        evaluated_ids.add(rid)
        new_count += 1
        tier_tag = "[S]" if is_s else ("[A]" if is_a_plus else ("[B]" if is_b_plus else "[C以下]"))
        print(f"  ✅ 集計{tier_tag}: {r_date} {venue}{r_num}R | 投資 {race_cost}円 -> 払戻 {race_payout}円")
        time.sleep(0.25)

    hit_rate = round(hit_count * 100.0 / max(1, total_bets), 1)
    rec_rate = round(total_ret * 100.0 / max(1, total_inv), 1)

    b_plus_stats = _finalize_tier_stats(b_plus_cnt)
    a_plus_stats = _finalize_tier_stats(a_plus_cnt)
    s_stats = _finalize_tier_stats(s_only_cnt)

    mark_stats_dict = {}
    mark_stats_list = []
    for sym, info in mark_counts.items():
        r_val = round(info["hit"] * 100.0 / max(1, info["total"]), 1)
        ratio_str = f"{info['hit']}/{info['total']}"
        entry = {
            "mark": sym, "symbol": sym, "key": info["eng"], "name": info["jp"], "label": info["full"],
            "rate": r_val, "placeRate": r_val, "fukushoRate": r_val, "in3Rate": r_val,
            "hitRate": r_val, "hit": info["hit"], "hits": info["hit"], "total": info["total"],
            "count": ratio_str, "countText": ratio_str, "ratio": ratio_str
        }
        for k in (sym, info["eng"], info["jp"], info["full"]):
            mark_stats_dict[k] = entry
        mark_stats_list.append(entry)

    stats.update({
        "hitRate": hit_rate,
        "recoveryRate": rec_rate,
        "roi": rec_rate,
        "totalBets": total_bets,
        "totalRaces": total_bets,
        "hitCount": hit_count,
        "hits": hit_count,
        "totalInvestment": total_inv,
        "totalCost": total_inv,
        "totalReturn": total_ret,
        "totalPayout": total_ret,
        "profit": total_ret - total_inv,
        "bPlusStats": b_plus_stats,
        "aPlusStats": a_plus_stats,
        "sStats": s_stats,
        "markStats": mark_stats_dict,
        "markStatsList": mark_stats_list,
        "markRates": mark_stats_dict,
        "hitDetails": hit_details[:100],
        "allBetRaces": all_bet_races[:200],
        "history": hit_details[:100],
        "results": all_bet_races[:200],
        "evaluatedRaceIds": sorted(list(evaluated_ids)),
    })

    os.makedirs("data", exist_ok=True)
    for sp in STATS_PATHS:
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    for tp in TODAY_PATHS:
        if os.path.exists(tp):
            try:
                with open(tp, "r", encoding="utf-8") as f:
                    td = json.load(f)
                if isinstance(td, dict):
                    td["stats"] = stats
                    td["hitRate"] = hit_rate
                    td["recoveryRate"] = rec_rate
                    td["roi"] = rec_rate
                    td["totalBets"] = total_bets
                    td["hitCount"] = hit_count
                    td["bPlusStats"] = b_plus_stats
                    td["aPlusStats"] = a_plus_stats
                    td["sStats"] = s_stats
                    td["hitDetails"] = stats["hitDetails"]
                    td["allBetRaces"] = stats["allBetRaces"]
                    with open(tp, "w", encoding="utf-8") as f:
                        json.dump(td, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    print(
        f"🏁 答え合わせ完了: 新規 {new_count}R | "
        f"全体: 的中率 {hit_rate}% ({hit_count}/{total_bets})・回収率 {rec_rate}% | "
        f"{_fmt_tier_log('B以上', b_plus_stats)} | "
        f"{_fmt_tier_log('A以上', a_plus_stats)} | "
        f"{_fmt_tier_log('S', s_stats)}"
    )


if __name__ == "__main__":
    main()
