import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

history_path = "data/history.json"
today_path = "data/today.json"

if not os.path.exists(history_path):
    print("history.json not found.")
    exit(0)

with open(history_path, "r", encoding="utf-8") as f:
    history = json.load(f)

if not os.path.exists(today_path):
    print("today.json not found.")
    exit(0)

with open(today_path, "r", encoding="utf-8") as f:
    today_data = json.load(f)

today_str = datetime.now().strftime("%Y-%m-%d")

# 各レースの結果を取得して判定
for race in today_data.get("races", []):
    race_id = race.get("raceId")
    if not race_id:
        continue

    # すでに集計済みならスキップ
    if any(r.get("raceId") == race_id and r.get("settled") for r in history["records"]):
        continue

    # netkeibaの結果画面をスクレイピング
    url = f"[https://race.netkeiba.com/race/result.html?race_id=](https://race.netkeiba.com/race/result.html?race_id=){race_id}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "EUC-JP"
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 1着馬番の取得
        first_row = soup.select_one(".ResultTableWrap tbody tr")
        if not first_row:
            continue
            
        num_cell = first_row.select_one(".Umaban")
        if not num_cell:
            continue
        first_num = int(num_cell.text.strip())

        # 単勝払戻金の取得
        payout_cell = soup.select_one(".Tansho .Payout")
        tansho_payout = int(re.sub(r"[^\d]", "", payout_cell.text)) if payout_cell else 0

        # 的中判定（本命馬が1着かどうか）
        honmei = race.get("honmeiNum")
        is_hit = (honmei == first_num)
        invest = 1000
        payout = tansho_payout * 10 if is_hit else 0

        record = {
            "raceId": race_id,
            "date": today_str,
            "venue": race["venue"],
            "raceName": race["raceName"],
            "honmei": {"num": honmei},
            "recommendation": race.get("aiBuy", ""),
            "invest": invest,
            "payout": payout,
            "isHit": is_hit,
            "settled": True
        }
        history["records"].append(record)
        history["totalInvest"] += invest
        history["totalPayout"] += payout
        history["totalRaces"] += 1
        if is_hit:
            history["hitRaces"] += 1

        print(f"Race {race_id} settled: Hit={is_hit}, Payout={payout}")
    except Exception as e:
        print(f"Error settling {race_id}: {e}")

with open(history_path, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

print("Results settlement completed.")
