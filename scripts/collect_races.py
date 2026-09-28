import os
import re
import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

os.makedirs("data", exist_ok=True)
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_kansai_and_graded_races():
    # 当日レース一覧ページを取得（netkeiba top）
    url = "https://race.netkeiba.com/top/"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "EUC-JP"
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print(f"Error fetching top: {e}")
        return []

    target_races = []
    
    # 開催会場ブロックを解析
    kaisai_blocks = soup.select(".RaceList_DataList > li")
    for block in kaisai_blocks:
        title_tag = block.select_one(".RaceList_DataTitle")
        if not title_tag:
            continue
        venue_name = title_tag.text.strip()
        
        # 関西会場（阪神、京都、中京）判定
        is_kansai = any(k in venue_name for k in ["阪神", "京都", "中京"])
        
        race_items = block.select(".RaceList_Item")
        for item in race_items:
            race_num_tag = item.select_one(".Race_Num")
            race_name_tag = item.select_one(".RaceName")
            time_tag = item.select_one(".Race_Time")
            link_tag = item.select_one("a")
            
            if not (race_num_tag and race_name_tag and link_tag):
                continue
                
            r_num = race_num_tag.text.strip()
            r_name = race_name_tag.text.strip()
            r_time = time_tag.text.strip() if time_tag else ""
            href = link_tag.get("href", "")
            
            # 重賞（G1, G2, G3, 重賞）判定
            is_graded = any(g in r_name for g in ["G1", "G2", "G3", "GI", "GII", "GIII", "(G", "重賞"])
            
            # 抽出条件: 関西全レース または 全国の重賞レース
            if is_kansai or is_graded:
                # race_id の抽出
                race_id_match = re.search(r"race_id=(\d+)", href)
                if race_id_match:
                    target_races.append({
                        "venue": venue_name[:2],
                        "raceNum": r_num,
                        "raceName": f"{r_num} {r_name}",
                        "startTime": r_time,
                        "isGraded": is_graded,
                        "raceId": race_id_match.group(1)
                    })
    return target_races

def scrape_shutuba(race_id):
    """各レースの出走馬一覧・オッズ・簡易スコア判定を取得"""
    url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
    horses = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "EUC-JP"
        soup = BeautifulSoup(res.text, "html.parser")
        
        rows = soup.select(".Shutuba_Table tbody tr")
        for row in rows:
            num_tag = row.select_one(".Umaban")
            name_tag = row.select_one(".HorseName a")
            jockey_tag = row.select_one(".Jockey a")
            odds_tag = row.select_one(".Popular")
            
            if num_tag and name_tag:
                num = num_tag.text.strip()
                name = name_tag.text.strip()
                jockey = jockey_tag.text.strip() if jockey_tag else ""
                odds_str = odds_tag.text.strip() if odds_tag else "---"
                
                # オッズ数値変換
                try:
                    odds = float(odds_str)
                except ValueError:
                    odds = 999.0
                    
                horses.append({
                    "num": int(num) if num.isdigit() else 0,
                    "name": name,
                    "jockey": jockey,
                    "odds": odds if odds != 999.0 else 0.0,
                    "score": 0.0,
                    "mark": "-"
                })
        time.sleep(1) # サーバー負荷防止
    except Exception as e:
        print(f"Error scraping {race_id}: {e}")
        
    # 簡易AIスコア・印の算出（オッズ基準での初期重み付け）
    if horses:
        valid_horses = [h for h in horses if h["odds"] > 0]
        valid_horses.sort(key=lambda x: x["odds"])
        marks = ["◎ 本命", "○ 対抗", "▲ 単穴", "☆ 穴", "△ 連下"]
        for idx, h in enumerate(valid_horses[:5]):
            h["mark"] = marks[idx]
            h["score"] = round(90.0 - (idx * 2.5), 1)
            
    return sorted(horses, key=lambda x: x["num"])

# メイン収集処理
print("Race scraping started...")
races_meta = get_kansai_and_graded_races()
final_races = []

for r in races_meta[:15]: # 取得対象件数の安全上限
    print(f"Fetching: {r['venue']} {r['raceName']}")
    horse_list = scrape_shutuba(r["raceId"])
    if horse_list:
        final_races.append({
            "venue": r["venue"],
            "raceName": r["raceName"],
            "startTime": r["startTime"],
            "isGraded": r["isGraded"],
            "horses": horse_list
        })

output_data = {
    "updatedAt": now_str,
    "races": final_races
}

with open("data/today.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"Complete! Extracted {len(final_races)} races.")
