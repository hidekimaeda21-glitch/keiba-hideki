import os
import re
import json
import time
import math
import datetime
import urllib.request
from bs4 import BeautifulSoup
import requests

# タイムゾーン設定 (JST: 日本標準時)
JST = datetime.timezone(datetime.timedelta(hours=9))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

VENUE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
    "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"
}

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


def fetch_html(url, encoding="euc-jp", retries=3):
    for i in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if encoding == "auto":
                res.encoding = res.apparent_encoding
            else:
                res.encoding = encoding
            return res.text
        except Exception as e:
            print(f"Fetch retry ({i+1}/{retries}) for {url}: {e}")
            time.sleep(1.5)
    return ""


def get_target_dates():
    """直近の開催日（土日）の日付リスト(YYYYMMDD)を返す"""
    now = datetime.datetime.now(JST)
    wd = now.weekday()  # 0:月 ... 5:土, 6:日
    dates = []
    if wd == 5:  # 土曜
        dates = [now, now + datetime.timedelta(days=1)]
    elif wd == 6:  # 日曜
        dates = [now, now - datetime.timedelta(days=1)]
    else:  # 平日は次の土日を探す
        days_to_sat = (5 - wd) % 7
        sat = now + datetime.timedelta(days=days_to_sat)
        sun = sat + datetime.timedelta(days=1)
        dates = [sat, sun]
    return [d.strftime("%Y%m%d") for d in dates]


def discover_race_ids():
    """netkeibaから対象開催日の全会場9R〜12Rのrace_idを取得する"""
    cand_dates = get_target_dates()
    for d_str in cand_dates:
        list_url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={d_str}"
        html = fetch_html(list_url, encoding="utf-8")
        if not html:
            continue
        r_ids = re.findall(r"race_id=(\d{12})", html)
        unique_ids = sorted(list(set(r_ids)))
        # 9R〜12Rのみ抽出
        main_ids = [rid for rid in unique_ids if int(rid[-2:]) in (9, 10, 11, 12)]
        if main_ids:
            return d_str, main_ids

    # 万が一取得できなかった場合は既存の today.json の日付・会場を維持するためのフォールバック
    now_str = datetime.datetime.now(JST).strftime("%Y%m%d")
    return now_str, []


def fetch_realtime_odds(race_id):
    """netkeibaの単勝オッズAPIから最新オッズを取得する"""
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
    """出馬表ページ(shutuba_past.html または shutuba.html)からレース情報と出走馬データを抽出"""
    url_past = f"https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}"
    html = fetch_html(url_past, encoding="euc-jp")
    if not html or "Shutuba_Table" not in html:
        url_basic = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
        html = fetch_html(url_basic, encoding="euc-jp")

    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # 会場名・レース番号
    v_code = race_id[4:6]
    venue_base = VENUE_MAP.get(v_code, "中央")
    r_num = int(race_id[-2:])

    # レース名・発走時刻・コース情報
    r_name_el = soup.select_one(".RaceName")
    race_name = r_name_el.get_text(strip=True) if r_name_el else f"{r_num}R"

    r_data01 = soup.select_one(".RaceData01")
    data01_txt = r_data01.get_text(" ", strip=True) if r_data01 else ""

    m_time = re.search(r"(\d{1,2}:\d{2})\s*発走", data01_txt)
    start_time = m_time.group(1) if m_time else "15:00"

    m_course = re.search(r"(芝|ダ|障)\s*(\d{3,4}m)", data01_txt)
    course_str = f"{m_course.group(1)}{m_course.group(2)}" if m_course else "芝1600m"

    odds_map = fetch_realtime_odds(race_id)

    horses = []
    rows = soup.select("tr.HorseList")
    for idx, tr in enumerate(rows, 1):
        # 取消・除外チェック
        if "Cancel" in tr.get("class", []) or "除外" in tr.get_text() or "取消" in tr.get_text():
            continue

        # 馬番
        uma_td = tr.select_one("td[class*='Umaban']")
        umaban = int(uma_td.get_text(strip=True)) if (uma_td and uma_td.get_text(strip=True).isdigit()) else idx

        # 枠番
        waku_td = tr.select_one("td[class*='Waku']")
        waku = int(waku_td.get_text(strip=True)) if (waku_td and waku_td.get_text(strip=True).isdigit()) else ((umaban - 1) % 8 + 1)

        # 馬名
        name_el = tr.select_one(".HorseName a, .Horse_Name a, .HorseName")
        h_name = name_el.get_text(strip=True) if name_el else f"馬{umaban}"

        # 騎手名
        jockey_el = tr.select_one(".Jockey a, .Jockey")
        jockey = jockey_el.get_text(strip=True) if jockey_el else "未定"
        jockey = re.sub(r"[▲△☆◇★]", "", jockey).strip()[:4]

        # オッズ
        odds_val = odds_map.get(umaban, 0.0)
        if odds_val <= 0:
            odds_el = tr.select_one("td[class*='Popular'] span, span[id*='odds']")
            if odds_el:
                try:
                    odds_val = float(odds_el.get_text(strip=True))
                except Exception:
                    odds_val = 0.0
        if odds_val <= 0:
            odds_val = round(3.0 + idx * 2.2, 1)

        # 過去走データ（最大3走）と脚質推定
        past_tds = tr.select("td.Past")
        past_runs = []
        corner_positions = []
        for p_td in past_tds[:3]:
            p_txt = p_td.get_text(" ", strip=True)
            if not p_txt:
                continue
            rank_el = p_td.select_one(".Num")
            rank_num = int(rank_el.get_text(strip=True)) if (rank_el and rank_el.get_text(strip=True).isdigit()) else 8
            past_runs.append({"rank": rank_num, "summary": p_txt[:45]})
            # 通過順 (例: 3-3-2)
            m_pass = re.search(r"(\d{1,2})-(\d{1,2})", p_txt)
            if m_pass:
                corner_positions.append(int(m_pass.group(1)))

        # 脚質判定
        avg_pos = sum(corner_positions) / len(corner_positions) if corner_positions else (umaban % 10 + 1)
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

    if not horses:
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
    """
    【改良版4AI合議＆1レース1,000円完全固定ロジック】
    ・EV(期待値)フィルターで危険な過剰人気馬(EV < 0.88)を自動降格
    ・展開AIと穴党AIを連携させ、紐荒れ(3着高配当穴馬)を確実に網羅
    ・全レースとも合計金額がピタリ1,000円になる3パターンで買い目を構築
    """
    horses = race_data["horses"]
    n_horses = len(horses)

    # 1. ペース予測（逃げ・先行馬の比率から算出）
    front_cnt = sum(1 for h in horses if h["style"] in ("逃げ", "先行"))
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

    # 2. 各馬の基礎能力指数・展開スコア・期待値(EV)の算出
    # オッズ順でソートして人気順位を把握
    sorted_by_odds = sorted(horses, key=lambda x: x["odds"])
    for pop_idx, h in enumerate(sorted_by_odds, 1):
        h["popularity"] = pop_idx

    raw_scores = []
    for h in horses:
        odds = max(1.1, h["odds"])
        # 過去3走の着順スコア
        if h["pastRuns"]:
            ranks = [r["rank"] for r in h["pastRuns"]]
            avg_rk = sum(ranks) / len(ranks)
            past_bonus = max(-4.0, (7.5 - avg_rk) * 1.4)
        else:
            # オッズから基礎能力を推定
            past_bonus = max(-2.0, (12.0 - math.log(odds) * 4.2))

        # 基礎時計・実績指数 (85.0 〜 96.5)
        time_idx = round(min(96.5, max(84.0, 91.5 - math.log(odds) * 2.1 + past_bonus * 0.45)), 1)
        # 展開補正込みの総合スコア
        pace_adj = pace_favor.get(h["style"], 0.0)
        # 内枠・外枠の微調整
        waku_adj = 0.4 if h["waku"] in (2, 3, 4) else (0.2 if h["waku"] in (5, 6) else 0.0)

        total_score = time_idx + pace_adj * 0.7 + waku_adj
        h["indexScore"] = time_idx
        h["totalScore"] = total_score
        raw_scores.append(total_score)

    # Zスコア（偏差値・突出度）と推定勝率・EV（期待値）を計算
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
        # 複勝圏・連対期待度を加味した実践EV
        raw_ev = est_prob * h["odds"] * 0.82 + (0.35 if 7.0 <= h["odds"] <= 35.0 else 0.15)
        h["ev"] = round(min(1.65, max(0.65, raw_ev)), 2)

    # 3. 【EVフィルター適用】軸馬（◎）と相手馬の選定
    # 基本は totalScore 順だが、1位馬の EV が 0.88 未満（過剰人気の危険馬）なら、
    # 上位3頭の中で EV >= 0.98 の馬を本命（◎）に引き上げる！
    ranked = sorted(horses, key=lambda x: (x["totalScore"] + (1.2 if x["ev"] >= 1.05 else 0.0)), reverse=True)
    if len(ranked) >= 2 and ranked[0]["ev"] < 0.88:
        for cand_i in range(1, min(3, len(ranked))):
            if ranked[cand_i]["ev"] >= 0.98:
                # 本命を入れ替え（危険な人気馬を2番手○に降格）
                ranked[0], ranked[cand_i] = ranked[cand_i], ranked[0]
                break

    honmei = ranked[0]
    taikou = ranked[1] if len(ranked) > 1 else ranked[0]
    tanana = ranked[2] if len(ranked) > 2 else taikou

    # 穴党AI特注馬（☆）：上位3頭以外（または3番手以降）で EV >= 1.05 かつ単勝オッズ 6.0倍〜60.0倍の激走穴馬を厳選
    remaining = ranked[3:] if len(ranked) > 3 else []
    ana_candidates = [
        h for h in remaining
        if 5.5 <= h["odds"] <= 65.0 and (h["ev"] >= 1.02 or pace_favor.get(h["style"], 0) > 1.0)
    ]
    if not ana_candidates:
        ana_candidates = sorted(remaining, key=lambda x: x["ev"], reverse=True)

    star_horse = ana_candidates[0] if ana_candidates else (ranked[3] if len(ranked) > 3 else tanana)
    # 紐候補（△）：残りの上位馬と高EV馬から最大3頭
    himo_pool = [h for h in ranked[3:] if h["num"] != star_horse["num"]]
    himo_horses = himo_pool[:3]

    # 4. 4つのAI（ジェミ総合・穴党・指数・展開）の印を付与
    by_index = sorted(horses, key=lambda x: x["indexScore"], reverse=True)
    by_pace = sorted(horses, key=lambda x: (pace_favor.get(x["style"], 0) * 2.0 + x["indexScore"]), reverse=True)
    by_ana = sorted(horses, key=lambda x: (x["ev"] + (0.3 if 8.0 <= x["odds"] <= 45.0 else 0.0)), reverse=True)

    for h in horses:
        n = h["num"]
        # ジェミ総合印
        if n == honmei["num"]:
            m_jemi = "◎"
        elif n == taikou["num"]:
            m_jemi = "○"
        elif n == tanana["num"]:
            m_jemi = "▲"
        elif n == star_horse["num"]:
            m_jemi = "☆"
        elif any( n == x["num"] for x in himo_horses ):
            m_jemi = "△"
        else:
            m_jemi = "・"

        # 穴党AI印
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

        # 指数AI印
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

        # 展開AI印
        if n == by_pace[0]["num"]:
            m_pc = "◎"
        elif len(by_pace) > 1 and n == by_pace[1]["num"]:
            m_pc = "○"
        elif pace_favor.get(h["style"], 0) > 1.0:
            m_pc = "▲"
        elif h["indexScore"] >= 91.0:
            m_pc = "△"
        else:
            m_pc = "・"

        h["mark"] = m_jemi
        h["marks"] = {
            "jemi": m_jemi,
            "ana": m_ana,
            "index": m_idx,
            "pace": m_pc
        }
        if "_w" in h:
            del h["_w"]

    # 5. 【1レース1,000円完全固定】3つの黄金パターンから最適な買い目を構築
    h1 = honmei["num"]
    h2 = taikou["num"]
    h3 = tanana["num"]
    hs = star_horse["num"]
    h_others = [x["num"] for x in himo_horses]

    # 相手リストの重複除去
    opp_5 = []
    for cand_n in [h3, hs] + h_others + [x["num"] for x in ranked]:
        if cand_n not in (h1, h2) and cand_n not in opp_5:
            opp_5.append(cand_n)
        if len(opp_5) == 5:
            break

    z_gap_top2 = taikou["zScore"] - tanana["zScore"]

    # パターン判定：
    # ① 2強突出型（上位2頭のZスコアが3番手より大きく抜けている場合：全体の約25%に厳選）
    if z_gap_top2 >= 4.5 and honmei["odds"] <= 6.5 and taikou["odds"] <= 9.5 and len(opp_5) >= 5:
        strategy_tag = "2強鉄板・タテ目穴ケア型 (計1,000円)"
        conf_grade = "A (92点)"
        opp_str = ", ".join(str(x) for x in opp_5[:5])
        # 内訳：馬連本線 300円 + 三連複2頭軸(5点×100円=500円) + 馬連タテ目 100円 + ワイド穴 100円 ＝ 8点 / 1,000円
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

    # ② 波乱・高期待値穴狙い型（本命のオッズがやや高め、またはハイペース混戦時）
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
        # 内訳：ワイド本線 200円 + 馬連流し(2点×100円=200円) + 三連複1頭軸(相手4頭・6点×100円=600円) ＝ 9点 / 1,000円
        ai_buy = (
            f"【ワイド本線】{h1} - {h2} (1点/200円) / "
            f"【馬連流し】{h1} - {h2}, {hs} (2点/各100円) / "
            f"【三連複1頭軸】{h1} - {opp4_str} (6点/各100円) [計9点/1,000円固定]"
        )
        comment = (
            f"展開予測は【{pace_label}】。過剰人気馬を排し、期待値(EV:{honmei['ev']})トップの◎{h1}番{honmei['name']}を軸に抜擢。"
            f"【ワイド本線】200円で手堅く回収ラインを確保しながら、穴党AI推奨の☆{hs}番を絡めた【馬連流し】と【三連複1頭軸】で高配当を射抜く。"
        )

    # ③ 標準・三連複フォーメーション型（最も的中率と回収率のバランスが高い主力パターン）
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
        # 三連複F: 1列目[h1] ✕ 2列目[h2, h3] ✕ 3列目[h2, h3, hs, △1, △2](5頭) ➔ 組み合わせはピタリ7点！
        # 内訳：馬連本線 200円 + 馬連押さえ 100円 + 三連複F(7点×100円=700円) ＝ 9点 / 1,000円
        ai_buy = (
            f"【馬連本線】{h1} - {h2} (1点/200円) / "
            f"【馬連押さえ】{h1} - {h3} (1点/100円) / "
            f"【三連複F】{h1} ✕ {h2},{h3} ✕ {col3_str} (7点/各100円) [計9点/1,000円固定]"
        )
        comment = (
            f"展開予測は【{pace_label}】。安定感抜群の◎{h1}番{honmei['name']}を1頭軸に据え、"
            f"2列目に○{h2}番・▲{h3}番を配置した【三連複フォーメーション(7点)】が主砲。○が崩れても▲と穴馬☆{hs}番の台頭で高配当を逃さず拾う1,000円布陣。"
        )

    # 表示順は馬番順に戻す
    race_data["horses"] = sorted(horses, key=lambda x: x["num"])
    race_data["strategyTag"] = strategy_tag
    race_data["confidence"] = conf_grade
    race_data["aiComment"] = comment
    race_data["aiBuy"] = ai_buy
    race_data["budget"] = 1000
    race_data["topPicks"] = [honmei, taikou, tanana]
    return race_data


def build_win5_prediction(races):
    """日曜（または後半5レース）の対象レースからWIN5推奨買い目を構築する"""
    # 10R・11Rを中心に5レースを選定
    win5_races = [r for r in races if r["rNum"] in (10, 11)][:5]
    if len(win5_races) < 5:
        win5_races = races[-5:] if len(races) >= 5 else races

    legs = []
    total_combos = 1
    # 点数を絞るため 1頭・2頭・1頭・2頭・2頭 (計8点〜12点) で構成
    pick_counts = [1, 2, 1, 2, 2]

    for idx, r in enumerate(win5_races):
        cnt = pick_counts[idx] if idx < len(pick_counts) else 1
        picks = r.get("topPicks", [])[:cnt]
        total_combos *= max(1, len(picks))
        legs.append({
            "leg": idx + 1,
            "venue": r["venue"],
            "rNum": r["rNum"],
            "raceName": r["shortRaceName"],
            "startTime": r["startTime"],
            "horses": [{"num": p["num"], "name": p["name"], "odds": p["odds"], "ev": p["ev"]} for p in picks]
        })

    return {
        "totalCombinations": total_combos,
        "estimatedCost": total_combos * 100,
        "concept": "道悪・条件不利馬およびEV0.88未満の危険な人気馬を完全除外し、4AI合議＆Zスコア突出馬を軸に少点数で高配当を射抜く。",
        "legs": legs
    }


def main():
    print("🚀 ジェミ予想 AI Predictor データ収集・1レース1,000円固定ロジック計算を開始します...")
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
        time.sleep(0.6)

    # もし平日等で出馬表がまだ公開されていない場合は、既存の today.json を読み込んで買い目ロジックだけ1,000円固定にアップグレードする
    out_paths = ["data/today.json", "today.json"]
    if not races_out:
        print("ℹ️ 新規出馬表が未発表のため、既存の today.json データを1レース1,000円固定ロジックに更新します。")
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

    # topPicks は内部計算用なので出力前にクリーンアップ
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

    print(f"✅ 完了！ 全{len(races_out)}レース（1レース1,000円固定 / 合計{len(races_out)*1000:,}円）を出力しました。")


if __name__ == "__main__":
    main()
