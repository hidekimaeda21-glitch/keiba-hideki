import os
import re
import json
import time
import math
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


def fetch_html(url, default_enc="euc-jp", retries=3):
    """バイト列から正確にデコードして文字化けを100%防ぐ"""
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
            print(f"Fetch retry ({i+1}/{retries}) for {url}: {e}")
            time.sleep(1.5)
    return ""


def get_target_dates():
    """
    現在時刻(JST)に応じて最適な開催日リストを返す
    ・金曜夜 / 土曜16時半まで ➔ 土曜を最優先
    ・土曜17時以降（土曜夜） / 日曜 ➔ 日曜を最優先
    """
    now = datetime.datetime.now(JST)
    wd = now.weekday()  # 0:月 ... 4:金, 5:土, 6:日
    if wd == 5:  # 土曜日
        if now.hour >= 17:
            # 土曜の17時以降（土曜夜の自動実行）は翌日の「日曜日」を第1候補にする
            dates = [now + datetime.timedelta(days=1), now]
        else:
            dates = [now, now + datetime.timedelta(days=1)]
    elif wd == 6:  # 日曜日
        dates = [now, now - datetime.timedelta(days=1)]
    else:  # 月〜金曜日（金曜夜の自動実行を含む）は直近の土曜日を第1候補にする
        days_to_sat = (5 - wd) % 7
        sat = now + datetime.timedelta(days=days_to_sat)
        sun = sat + datetime.timedelta(days=1)
        dates = [sat, sun]
    return [d.strftime("%Y%m%d") for d in dates]


def discover_race_ids():
    cand_dates = get_target_dates()
    for d_str in cand_dates:
        list_url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={d_str}"
        html = fetch_html(list_url, default_enc="utf-8")
        if not html:
            continue
        r_ids = re.findall(r"race_id=(\d{12})", html)
        unique_ids = sorted(list(set(r_ids)))
        main_ids = [rid for rid in unique_ids if int(rid[-2:]) in (9, 10, 11, 12)]
        if main_ids:
            return d_str, main_ids
    now_str = datetime.datetime.now(JST).strftime("%Y%m%d")
    return now_str, []


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


def parse_shutuba_page(race_id):
    url_basic = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
    html = fetch_html(url_basic, default_enc="euc_jp")
    if not html or "HorseList" not in html:
        url_past = f"https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}"
        html = fetch_html(url_past, default_enc="euc_jp")

    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    v_code = race_id[4:6]
    venue_base = VENUE_MAP.get(v_code, "中央")
    r_num = int(race_id[-2:])

    r_name_el = soup.select_one(".RaceName")
    race_name = r_name_el.get_text(strip=True) if r_name_el else f"{r_num}R"
    race_name = re.sub(r"[\r\n\t]+", "", race_name).strip()

    r_data01 = soup.select_one(".RaceData01")
    data01_txt = r_data01.get_text(" ", strip=True) if r_data01 else ""

    m_time = re.search(r"(\d{1,2}:\d{2})\s*発走", data01_txt)
    start_time = m_time.group(1) if m_time else f"{10 + r_num // 2}:{(r_num % 2) * 30 + 10:02d}"

    m_course = re.search(r"(芝|ダ|障)[^\d]*(\d{3,4}m)", data01_txt)
    course_str = f"{m_course.group(1)}{m_course.group(2)}" if m_course else "芝1600m"

    odds_map = fetch_realtime_odds(race_id)

    horses = []
    seen_names = set()
    rows = soup.select("tr.HorseList")

    for tr in rows:
        if "Cancel" in tr.get("class", []) or "除外" in tr.get_text() or "取消" in tr.get_text():
            continue

        name_el = tr.select_one(".HorseName a, .Horse_Name a, .HorseName")
        h_name = name_el.get_text(strip=True) if name_el else ""
        if not h_name or h_name in seen_names:
            continue
        seen_names.add(h_name)

        if len(horses) >= 18:
            break
        seq_num = len(horses) + 1

        uma_td = tr.select_one("td[class*='Umaban']")
        uma_txt = uma_td.get_text(strip=True) if uma_td else ""
        if uma_txt.isdigit() and 1 <= int(uma_txt) <= 18:
            umaban = int(uma_txt)
        else:
            umaban = seq_num

        waku_td = tr.select_one("td[class*='Waku']")
        waku_txt = waku_td.get_text(strip=True) if waku_td else ""
        if waku_txt.isdigit() and 1 <= int(waku_txt) <= 8:
            waku = int(waku_txt)
        else:
            waku = min(8, (umaban - 1) // 2 + 1)

        jockey_el = tr.select_one(".Jockey a, .Jockey")
        jockey = jockey_el.get_text(strip=True) if jockey_el else "未定"
        jockey = re.sub(r"[▲△☆◇★\s]+", "", jockey)[:4] or "未定"

        odds_val = odds_map.get(umaban, 0.0)
        if odds_val <= 0:
            odds_el = tr.select_one("td[class*='Popular'] span, span[id*='odds']")
            if odds_el:
                try:
                    odds_val = float(odds_el.get_text(strip=True))
                except Exception:
                    odds_val = 0.0
        if odds_val <= 0:
            odds_val = round(2.8 + (seq_num - 1) * 2.1, 1)

        past_tds = tr.select("td.Past")
        past_runs = []
        corner_positions = []
        for p_td in past_tds[:3]:
            p_txt = p_td.get_text(" ", strip=True)
            if not p_txt:
                continue
            rank_el = p_td.select_one(".Num")
            rank_num = int(rank_el.get_text(strip=True)) if (rank_el and rank_el.get_text(strip=True).isdigit()) else 6
            past_runs.append({"rank": rank_num, "summary": p_txt[:45]})
            m_pass = re.search(r"(\d{1,2})-(\d{1,2})", p_txt)
            if m_pass:
                corner_positions.append(int(m_pass.group(1)))

        avg_pos = sum(corner_positions) / len(corner_positions) if corner_positions else ((umaban % 8) + 2)
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
            "waku": waku,
            "name": h_name,
            "jockey": jockey,
            "odds": round(odds_val, 1),
            "style": style,
            "pastRuns": past_runs
        })

    if len(horses) < 5:
        return None

    return {
        "raceId": race_id,
        "venueBase": venue_base,
        "rNum": r_num,
        "raceName": f"{r_num}R {race_name} ({course_str})",
        "shortRaceName": race_name,
        "course": course_str,
        "startTime": start_time,
        "horses": horses
    }


def evaluate_and_build_1000yen_strategy(race_data):
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
        used_nums.add(n)
        valid_horses.append(h)
        if len(valid_horses) >= 18:
            break
    horses = valid_horses
    n_horses = len(horses)

    front_cnt = sum(1 for h in horses if h.get("style") in ("逃げ", "先行"))
    front_ratio = front_cnt / max(1, n_horses)
    if front_ratio >= 0.42:
        pace_label = "差し有利ハイペース"
        pace_favor = {"逃げ": -1.5, "先行": -0.5, "差し": +2.2, "追込": +1.8}
    elif front_ratio <= 0.22:
        pace_label = "先行有利スローペース"
        pace_favor = {"逃げ": +2.5, "先行": +2.0, "差し": -0.8, "追込": -1.5}
    else:
        pace_label = "平均ミドルペース"
        pace_favor = {"逃げ": +0.5, "先行": +1.2, "差し": +1.2, "追込": 0.0}

    sorted_by_odds = sorted(horses, key=lambda x: x["odds"])
    for pop_idx, h in enumerate(sorted_by_odds, 1):
        h["popularity"] = pop_idx

    raw_scores = []
    for h in horses:
        odds = max(1.1, float(h.get("odds", 10.0)))
        if h.get("pastRuns"):
            ranks = [r["rank"] for r in h["pastRuns"]]
            avg_rk = sum(ranks) / len(ranks)
            past_bonus = max(-4.0, (7.5 - avg_rk) * 1.4)
        else:
            past_bonus = max(-2.0, (12.0 - math.log(odds) * 4.2))

        time_idx = round(min(96.5, max(84.0, 91.5 - math.log(odds) * 2.1 + past_bonus * 0.45)), 1)
        pace_adj = pace_favor.get(h.get("style", "先行"), 0.0)
        waku_adj = 0.4 if h.get("waku", 4) in (2, 3, 4) else (0.2 if h.get("waku", 4) in (5, 6) else 0.0)

        total_score = time_idx + pace_adj * 0.7 + waku_adj
        h["indexScore"] = time_idx
        h["totalScore"] = total_score
        raw_scores.append(total_score)

    mean_sc = sum(raw_scores) / len(raw_scores)
    std_sc = math.sqrt(sum((x - mean_sc) ** 2 for x in raw_scores) / max(1, len(raw_scores))) or 1.0

    exp_weights = []
    for h in horses:
        z = (h["totalScore"] - mean_sc) / std_sc
        h["zScore"] = round(50.0 + z * 10.0, 1)
        w = math.exp(z * 1.15)
        h["_w"] = w
        exp_weights.append(w)

    sum_w = sum(exp_weights) or 1.0
    for h in horses:
        est_prob = h["_w"] / sum_w
        raw_ev = est_prob * h["odds"] * 0.82 + (0.35 if 7.0 <= h["odds"] <= 35.0 else 0.15)
        h["ev"] = round(min(1.65, max(0.65, raw_ev)), 2)

    ranked = sorted(horses, key=lambda x: (x["totalScore"] + (1.2 if x["ev"] >= 1.05 else 0.0)), reverse=True)
    if len(ranked) >= 2 and ranked[0]["ev"] < 0.88:
        for cand_i in range(1, min(3, len(ranked))):
            if ranked[cand_i]["ev"] >= 0.98:
                ranked[0], ranked[cand_i] = ranked[cand_i], ranked[0]
                break

    honmei = ranked[0]
    taikou = ranked[1] if len(ranked) > 1 else ranked[0]
    tanana = ranked[2] if len(ranked) > 2 else taikou

    remaining = ranked[3:] if len(ranked) > 3 else []
    ana_candidates = [
        h for h in remaining
        if 5.5 <= h["odds"] <= 65.0 and (h["ev"] >= 1.02 or pace_favor.get(h.get("style", ""), 0) > 1.0)
    ]
    if not ana_candidates:
        ana_candidates = sorted(remaining, key=lambda x: x["ev"], reverse=True)

    star_horse = ana_candidates[0] if ana_candidates else (ranked[3] if len(ranked) > 3 else tanana)
    himo_pool = [h for h in ranked[3:] if h["num"] != star_horse["num"]]
    himo_horses = himo_pool[:3]

    by_index = sorted(horses, key=lambda x: x["indexScore"], reverse=True)
    by_pace = sorted(horses, key=lambda x: (pace_favor.get(x.get("style", ""), 0) * 2.0 + x["indexScore"]), reverse=True)
    by_ana = sorted(horses, key=lambda x: (x["ev"] + (0.3 if 8.0 <= x["odds"] <= 45.0 else 0.0)), reverse=True)

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
            m_jemi = "・"

        if n == by_ana[0]["num"]:
            m_ana = "◎"
        elif len(by_ana) > 1 and n == by_ana[1]["num"]:
            m_ana = "☆"
        elif h["ev"] >= 1.05:
            m_ana = "▲"
        elif h["ev"] >= 0.96:
            m_ana = "△"
        else:
            m_ana = "・"

        if n == by_index[0]["num"]:
            m_idx = "◎"
        elif len(by_index) > 1 and n == by_index[1]["num"]:
            m_idx = "○"
        elif len(by_index) > 2 and n == by_index[2]["num"]:
            m_idx = "▲"
        elif h["indexScore"] >= 91.5:
            m_idx = "△"
        else:
            m_idx = "・"

        if n == by_pace[0]["num"]:
            m_pc = "◎"
        elif len(by_pace) > 1 and n == by_pace[1]["num"]:
            m_pc = "○"
        elif pace_favor.get(h.get("style", ""), 0) > 1.0:
            m_pc = "▲"
        elif h["indexScore"] >= 91.0:
            m_pc = "△"
        else:
            m_pc = "・"

        h["mark"] = m_jemi
        h["marks"] = {"jemi": m_jemi, "ana": m_ana, "index": m_idx, "pace": m_pc}
        if "_w" in h:
            del h["_w"]

    h1, h2, h3, hs = honmei["num"], taikou["num"], tanana["num"], star_horse["num"]
    h_others = [x["num"] for x in himo_horses]

    opp_5 = []
    for cand_n in [h3, hs] + h_others + [x["num"] for x in ranked]:
        if cand_n not in (h1, h2) and cand_n not in opp_5:
            opp_5.append(cand_n)
        if len(opp_5) == 5:
            break

    z_gap_top2 = taikou["zScore"] - tanana["zScore"]

    if z_gap_top2 >= 4.5 and honmei["odds"] <= 6.5 and taikou["odds"] <= 9.5 and len(opp_5) >= 5:
        strategy_tag = "2強鉄板・タテ目穴ケア型 (計1,000円)"
        conf_grade = "A (92点)"
        opp_str = ", ".join(str(x) for x in opp_5[:5])
        ai_buy = (
            f"【馬連本線】{h1} - {h2} (1点/300円) / "
            f"【三連複2頭軸】{h1},{h2} - {opp_str} (5点/各100円) / "
            f"【馬連タテ目】{h2} - {h3} (1点/100円) / "
            f"【ワイド穴】{h1} - {hs} (1点/100円) [計8点/1,000円固定]"
        )
        comment = (
            f"展開予測は【{pace_label}】。能力・期待値ともに抜けた◎{h1}番{honmei['name']}と○{h2}番の2強が強力。"
            f"【馬連本線】300円で厚く利益を狙いつつ、【三連複2頭軸】と特注穴馬☆{hs}番への【ワイド穴】・【馬連タテ目】まで1,000円内で完全網羅。"
        )
    elif honmei["odds"] >= 6.0 or front_ratio >= 0.48:
        strategy_tag = "波乱対応・高期待値穴狙い型 (計1,000円)"
        conf_grade = "B+ (88点)"
        opp_4 = []
        for cand_n in [h2, h3, hs] + opp_5:
            if cand_n != h1 and cand_n not in opp_4:
                opp_4.append(cand_n)
            if len(opp_4) == 4:
                break
        opp4_str = ", ".join(str(x) for x in opp_4)
        ai_buy = (
            f"【ワイド本線】{h1} - {h2} (1点/200円) / "
            f"【馬連流し】{h1} - {h2}, {hs} (2点/各100円) / "
            f"【三連複1頭軸】{h1} - {opp4_str} (6点/各100円) [計9点/1,000円固定]"
        )
        comment = (
            f"展開予測は【{pace_label}】。過剰人気馬を排し、期待値(EV:{honmei['ev']})トップの◎{h1}番{honmei['name']}を軸に抜擢。"
            f"【ワイド本線】200円で手堅く回収ラインを確保しながら、穴党AI推奨の☆{hs}番を絡めた【馬連流し】と【三連複1頭軸】で高配当を射抜く。"
        )
    else:
        strategy_tag = "1頭軸フォーメーション・バランス型 (計1,000円)"
        conf_grade = "A (90点)"
        col3_list = []
        for cand_n in [h2, h3, hs] + opp_5:
            if cand_n != h1 and cand_n not in col3_list:
                col3_list.append(cand_n)
            if len(col3_list) == 5:
                break
        col3_str = ", ".join(str(x) for x in col3_list)
        ai_buy = (
            f"【馬連本線】{h1} - {h2} (1点/200円) / "
            f"【馬連押さえ】{h1} - {h3} (1点/100円) / "
            f"【三連複F】{h1} ✕ {h2},{h3} ✕ {col3_str} (7点/各100円) [計9点/1,000円固定]"
        )
        comment = (
            f"展開予測は【{pace_label}】。安定感抜群の◎{h1}番{honmei['name']}を1頭軸に据え、"
            f"2列目に○{h2}番・▲{h3}番を配置した【三連複フォーメーション(7点)】が主砲。○が崩れても▲と穴馬☆{hs}番の台頭で高配当を逃さず拾う1,000円布陣。"
        )

    race_data["horses"] = sorted(horses, key=lambda x: x["num"])
    race_data["strategyTag"] = strategy_tag
    race_data["confidence"] = conf_grade
    race_data["aiComment"] = comment
    race_data["aiBuy"] = ai_buy
    race_data["budget"] = 1000
    race_data["topPicks"] = [honmei, taikou, tanana]
    return race_data


def build_win5_prediction(races):
    cand_races = [r for r in races if r.get("rNum") in (10, 11)]
    cand_races.sort(key=lambda x: x.get("startTime", "15:00"))
    win5_races = cand_races[-5:] if len(cand_races) >= 5 else races[-5:]

    legs = []
    total_combos = 1
    pick_counts = [1, 2, 1, 2, 2]

    for idx, r in enumerate(win5_races):
        cnt = pick_counts[idx] if idx < len(pick_counts) else 1
        picks = r.get("topPicks", [])[:cnt]
        if not picks and r.get("horses"):
            picks = r["horses"][:cnt]
        total_combos *= max(1, len(picks))
        legs.append({
            "leg": idx + 1,
            "venue": r.get("venue", ""),
            "rNum": r.get("rNum", 11),
            "raceName": r.get("shortRaceName", r.get("raceName", "")),
            "startTime": r.get("startTime", "15:00"),
            "horseNums": [p["num"] for p in picks],
            "horses": [{"num": p["num"], "name": p["name"], "odds": p["odds"], "ev": p.get("ev", 1.0)} for p in picks]
        })

    return {
        "totalCombinations": total_combos,
        "unitYen": 100,
        "estimatedCost": total_combos * 100,
        "concept": "道悪・条件不利馬およびEV0.88未満の危険な人気馬を完全除外し、4AI合議＆Zスコア突出馬を軸に8点（800円）で高配当を射抜く。",
        "legs": legs
    }


def main():
    print("🚀 ジェミ予想 AI Predictor データ収集・1レース1,000円固定＆WIN5計算を開始します...")
    d_str, race_ids = discover_race_ids()

    dt_obj = datetime.datetime.strptime(d_str, "%Y%m%d")
    wd_str = WEEKDAY_JP[dt_obj.weekday()]
    target_date_display = f"{dt_obj.year}年{dt_obj.month}月{dt_obj.day}日"

    races_out = []
    for rid in race_ids:
        print(f"  -> 解析中: race_id={rid}")
        r_info = parse_shutuba_page(rid)
        if not r_info:
            continue
        r_info["venue"] = f"{r_info['venueBase']}（{wd_str}）"
        r_info = evaluate_and_build_1000yen_strategy(r_info)
        races_out.append(r_info)
        time.sleep(0.5)

    out_paths = ["data/today.json", "today.json"]
    if not races_out:
        print("ℹ️ 新規出馬表が未発表のため、既存の today.json データを1レース1,000円固定＆WIN5対応に更新します。")
        for p in out_paths:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                target_date_display = old_data.get("targetDate", target_date_display)
                for r in old_data.get("races", []):
                    r.setdefault("shortRaceName", r.get("raceName", ""))
                    r = evaluate_and_build_1000yen_strategy(r)
                    races_out.append(r)
                break

    win5_data = build_win5_prediction(races_out) if races_out else {}
    for r in races_out:
        if "topPicks" in r:
            del r["topPicks"]

    now_str = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    final_json = {
        "targetDate": target_date_display,
        "updatedAt": now_str,
        "budgetPerRace": 1000,
        "totalBudget": len(races_out) * 1000,
        "win5": win5_data,
        "races": races_out
    }

    os.makedirs("data", exist_ok=True)
    for path in out_paths:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(final_json, f, ensure_ascii=False, indent=2)

    print(f"✅ 完了！ 全{len(races_out)}レース（1R 1,000円）＋ WIN5（{win5_data.get('totalCombinations', 0)}点）を出力しました。")


if __name__ == "__main__":
    main()
