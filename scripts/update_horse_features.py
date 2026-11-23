import os
import re
import sys
import json
import time
import argparse
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

HORSE_FEATURES_PATH = "data/horse_features.json"


def _norm_name(name):
    return re.sub(r"\s+", "", str(name or "")).strip()


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


def calc_pci(time_sec, agari, dist):
    if time_sec <= 0 or agari <= 0 or dist <= 600 or time_sec <= agari:
        return 50.0
    return round(((time_sec - agari) / agari) * (600.0 / (dist - 600.0)) * 100.0, 1)


def parse_time_sec(txt):
    m = re.search(r"(\d):(\d{2}\.\d)", str(txt or ""))
    if m:
        return round(int(m.group(1)) * 60 + float(m.group(2)), 1)
    m2 = re.search(r"(\d{2}\.\d)", str(txt or ""))
    if m2:
        return float(m2.group(1))
    return 0.0


def load_existing_db(path=HORSE_FEATURES_PATH):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_db(db, path=HORSE_FEATURES_PATH):
    # 365日以上前の古い自動レコードを整理して軽量維持
    cutoff = (datetime.datetime.now(JST) - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    cleaned = {}
    for k, v in db.items():
        if not isinstance(v, dict):
            continue
        upd = str(v.get("updated_at", ""))
        if v.get("source") != "manual" and re.match(r"^\d{4}-\d{2}-\d{2}$", upd) and upd < cutoff:
            continue
        cleaned[k] = v

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    return len(cleaned)


def collect_race_ids_for_date(d_str, target_rnums):
    url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={d_str}"
    html = fetch_html(url, default_enc="utf-8")
    if not html:
        return []
    r_ids = sorted(list(set(re.findall(r"race_id=(\d{12})", html))))
    return [rid for rid in r_ids if int(rid[-2:]) in target_rnums]


def analyze_race_result(race_id, race_date_iso):
    """
    確定レース結果ページ（result.html）を解析し、次走狙い目となる
    「脚余し不発・ハイペース先行潰れ・ドスロー後方不発・外枠距離ロス僅差」馬を抽出する。
    """
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    html = fetch_html(url, default_enc="euc_jp")
    if not html or "RaceTable01" not in html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    v_name = VENUE_MAP.get(race_id[4:6], "")
    r_num = int(race_id[-2:])
    r_name_el = soup.select_one(".RaceName")
    r_name = re.sub(r"\s+", "", r_name_el.get_text(strip=True)) if r_name_el else f"{r_num}R"

    data01_el = soup.select_one(".RaceData01")
    data01_txt = data01_el.get_text(" ", strip=True) if data01_el else ""
    m_dist = re.search(r"(?:芝|ダ|障)[^\d]*(\d{3,4})", data01_txt)
    dist = int(m_dist.group(1)) if m_dist else 1600

    rows = soup.select("table.RaceTable01 tbody tr, table.RaceTable01 tr.HorseList")
    finishers = []
    for tr in rows:
        tds = tr.select("td")
        if len(tds) < 12:
            continue
        rk_txt = tds[0].get_text(strip=True)
        if not rk_txt.isdigit():
            continue
        rank = int(rk_txt)
        waku_txt = tds[1].get_text(strip=True)
        waku = int(waku_txt) if waku_txt.isdigit() else 4

        name_el = tr.select_one(".Horse_Name a, .HorseName a") or tds[3]
        h_name = _norm_name(name_el.get_text(strip=True))
        if not h_name:
            continue

        time_sec = parse_time_sec(tds[7].get_text(strip=True))
        agari_txt = tds[11].get_text(strip=True)
        try:
            agari = float(agari_txt)
        except Exception:
            agari = 0.0

        pass_txt = tds[12].get_text(strip=True) if len(tds) > 12 else ""
        pass_nums = [int(x) for x in re.findall(r"\d+", pass_txt)]
        pass1 = pass_nums[0] if pass_nums else 0
        pass4 = pass_nums[-1] if pass_nums else 0

        finishers.append({
            "name": h_name,
            "rank": rank,
            "waku": waku,
            "timeSec": time_sec,
            "agari": agari,
            "pass1": pass1,
            "pass4": pass4,
        })

    if len(finishers) < 6:
        return {}

    winner_time = min((f["timeSec"] for f in finishers if f["timeSec"] > 0), default=0.0)
    valid_agari = sorted(set(f["agari"] for f in finishers if 28.0 <= f["agari"] <= 46.0))
    agari_rank_map = {val: idx + 1 for idx, val in enumerate(valid_agari)}

    extracted = {}
    short_date = race_date_iso[5:].replace("-", "/")

    for f in finishers:
        rank = f["rank"]
        if rank <= 2:
            # 1〜2着馬は次走で普通に人気になるため、隠れ実力馬（3着以下・特に4着以下）に絞る
            continue

        time_diff = round(max(0.0, f["timeSec"] - winner_time), 1) if (f["timeSec"] > 0 and winner_time > 0) else 0.5
        agari = f["agari"]
        agari_rk = agari_rank_map.get(agari, 99)
        pci = calc_pci(f["timeSec"], agari, dist)
        pass1, pass4, waku = f["pass1"], f["pass4"], f["waku"]

        traffic_disadv = 0
        corner_radius = 1.0
        finish_effort = 0.0
        bonus = 0.0
        reasons = []

        # 1. 脚余し不発（上がり1〜3位なのに4着以下・僅差）
        if agari_rk <= 3 and rank >= 4 and time_diff <= 0.9:
            finish_effort = 1.0
            if agari_rk == 1 and rank >= 5 and time_diff <= 0.6:
                traffic_disadv = 2
                bonus += 2.5
                reasons.append(f"上がり最速({agari}秒)も{rank}着・脚余し")
            else:
                traffic_disadv = 1
                bonus += 1.8
                reasons.append(f"上がり{agari_rk}位({agari}秒)も{rank}着・不発")

        # 2. 超ハイペース先行潰れ（PCI < 47 で先行して大敗）
        if pci < 47.0 and (1 <= pass1 <= 4) and rank >= 5 and time_diff <= 1.6:
            bonus += 2.2
            reasons.append(f"超ハイ(PCI:{pci})先行で展開負け")

        # 3. ドスロー後方不発（PCI > 53 で後方から届かず）
        if pci > 53.0 and (pass1 >= 8 or pass4 >= 8) and rank >= 4 and time_diff <= 0.8:
            finish_effort = 1.0
            bonus += 2.0
            reasons.append(f"ドスロー(PCI:{pci})後方届かず")

        # 4. 外枠距離ロス僅差負け（7〜8枠で0.5秒差以内）
        if waku in (7, 8) and 4 <= rank <= 7 and time_diff <= 0.5:
            corner_radius = 1.5
            bonus += 1.4
            reasons.append(f"{waku}枠外回りロスも{time_diff:.1f}秒差")

        if bonus >= 1.4 and reasons:
            final_bonus = round(min(4.0, bonus), 1)
            extracted[f["name"]] = {
                "traffic_disadvantage": traffic_disadv,
                "corner_radius": corner_radius,
                "finish_effort": finish_effort,
                "video_bonus": final_bonus,
                "memo": f"{short_date} {v_name}{r_num}R({r_name}): " + "・".join(reasons[:2]),
                "source": "auto_result",
                "updated_at": race_date_iso,
            }

    return extracted


def main():
    parser = argparse.ArgumentParser(description="JRAレース結果から馬別定性DB（data/horse_features.json）を自動更新")
    parser.add_argument("--days", type=int, default=7, help="遡る日数（週明け自動収集=7 / 1年分バックフィル=365）")
    args = parser.parse_args()

    days = max(1, min(366, args.days))
    # 週明け収集(<=14日)は9R〜12R全レース、長期バックフィル(>14日)は11Rメイン(重賞・OP)に絞って高速実行
    target_rnums = (9, 10, 11, 12) if days <= 14 else (11,)

    print(f"🔍 過去{days}日間のレース結果から定性DBを自動更新します（対象R: {target_rnums}）...")
    db = load_existing_db()
    now = datetime.datetime.now(JST)

    total_races = 0
    updated_horses = 0

    for offset in range(0, days):
        dt = now - datetime.timedelta(days=offset)
        # 土・日・月（祝日開催含む）のみチェックして無駄なアクセスを削減
        if dt.weekday() not in (5, 6, 0):
            continue
        d_str = dt.strftime("%Y%m%d")
        d_iso = dt.strftime("%Y-%m-%d")

        rids = collect_race_ids_for_date(d_str, target_rnums)
        if not rids:
            continue

        print(f"  📅 {d_iso}: {len(rids)}レースを解析中...")
        for rid in rids:
            feats = analyze_race_result(rid, d_iso)
            total_races += 1
            for h_name, feat in feats.items():
                prev = db.get(h_name)
                # 手動登録（動画確認メモ）が同日以降にある場合は上書きしない
                if isinstance(prev, dict) and prev.get("source") == "manual" and str(prev.get("updated_at", "")) >= d_iso:
                    continue
                # 既存レコードより新しい開催日（または未登録）のみ更新
                if not isinstance(prev, dict) or str(prev.get("updated_at", "")) <= d_iso:
                    db[h_name] = feat
                    updated_horses += 1
            time.sleep(0.25)

    total_saved = save_db(db)
    print(f"✅ 完了！ {total_races}レース解析 / {updated_horses}頭を新規・更新（DB総数: {total_saved}頭）")


if __name__ == "__main__":
    main()
