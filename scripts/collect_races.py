import os
import re
import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from google import genai

os.makedirs("data", exist_ok=True)
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
today_date = datetime.now().strftime("%Y-%m-%d")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def ask_gemini_prediction(race_name, venue, horses):
    """Gemini 3.8 Flash に展開・直近走を考慮した推論を行わせる"""
    if not client or not horses:
        return {"summary": "APIキー未設定または出走馬なし", "recommendation": "単勝・複勝", "honmei_num": 1}

    horse_summary = "\n".join([
        f"{h['num']}番 {h['name']} (騎手:{h['jockey']}, 単勝:{h['odds']}倍, 近走:{h.get('recent', '情報収集中')}, 印:{h.get('mark', '-')})"
        for h in horses[:12]
    ])
    prompt = f"""
あなたはプロの競馬AI予想家「ジェミ予想」です。
以下のレース出走表と各馬の近走状況を分析し、展開や有力馬・妙味馬の理由、および推奨買い目を提示してください。

会場: {venue}
レース名: {race_name}
出走馬情報:
{horse_summary}

必ず以下のJSON形式のみを出力してください（Markdownコードブロックは不要です）:
{{
  "honmei_num": 本命馬の馬番(半角数字),
  "summary": "展開予測と本命・穴馬を推奨する根拠（100〜140文字程度）",
  "recommendation": "推奨買い目（例：単勝 13 / 馬連 13-1,2 / 3連複 13-2,5-1,2,5など）"
}}
"""
    candidate_models = ['gemini-3.8-flash', 'gemini-3.5-flash', 'gemini-3.5-flash-lite']
    last_error = ""

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            text = response.text.strip()
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)
            if "honmei_num" not in data:
                data["honmei_num"] = horses[0]["num"] if horses else 1
            return data
        except Exception as e:
            last_error = str(e)
            continue

    print(f"Gemini API Error: {last_error}")
    return {
        "honmei_num": horses[0]["num"] if horses else 1,
        "summary": "直近成績とオッズ妙味を考慮した推奨構成です。",
        "recommendation": "単勝・馬連流し"
    }

def get_live_races():
    url = "[https://race.netkeiba.com/top/](https://race.netkeiba.com/top/)"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "EUC-JP"
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print(f"Error fetching top: {e}")
        return []

    target_races = []
    kaisai_blocks = soup.select(".RaceList_DataList > li")
    for block in kaisai_blocks:
        title_tag = block.select_one(".RaceList_DataTitle")
        if not title_tag:
            continue
        venue_name = title_tag.text.strip()
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
            
            is_graded = any(g in r_name for g in ["G1", "G2", "G3", "GI", "GII", "GIII", "重賞"])
            
            if is_kansai or is_graded:
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
    url = f"[https://race.netkeiba.com/race/shutuba.html?race_id=](https://race.netkeiba.com/race/shutuba.html?race_id=){race_id}"
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
            
            # 直近走の簡易取得（過去走着順列）
            recent_cells = row.select(".PastRun_Data")
            recents = [c.text.strip() for c in recent_cells[:3] if c.text.strip()]
            recent_str = "/".join(recents) if recents else "近走データ集計中"

            if num_tag and name_tag:
                num = num_tag.text.strip()
                name = name_tag.text.strip()
                jockey = jockey_tag.text.strip() if jockey_tag else ""
                odds_str = odds_tag.text.strip() if odds_tag else "---"
                try:
                    odds = float(odds_str)
                except ValueError:
                    odds = 999.0
                    
                horses.append({
                    "num": int(num) if num.isdigit() else 0,
                    "name": name,
                    "jockey": jockey,
                    "odds": odds if odds != 999.0 else 0.0,
                    "recent": recent_str,
                    "score": 0.0,
                    "mark": "-"
                })
        time.sleep(1)
    except Exception as e:
        print(f"Error scraping {race_id}: {e}")
        
    if horses:
        valid_horses = [h for h in horses if h["odds"] > 0]
        valid_horses.sort(key=lambda x: x["odds"])
        marks = ["◎ 本命", "○ 対抗", "▲ 単穴", "☆ 穴", "△ 連下"]
        for idx, h in enumerate(valid_horses[:5]):
            h["mark"] = marks[idx]
            h["score"] = round(92.0 - (idx * 2.8), 1)
            
    return sorted(horses, key=lambda x: x["num"])

print("Collecting race information...")
live_meta = get_live_races()
final_races = []

if live_meta:
    for r in live_meta[:10]:
        h_list = scrape_shutuba(r["raceId"])
        if h_list:
            ai_insight = ask_gemini_prediction(r["raceName"], r["venue"], h_list)
            final_races.append({
                "raceId": r["raceId"],
                "venue": r["venue"],
                "raceName": r["raceName"],
                "startTime": r["startTime"],
                "isGraded": r["isGraded"],
                "horses": h_list,
                "honmeiNum": ai_insight.get("honmei_num"),
                "aiSummary": ai_insight.get("summary", ""),
                "aiBuy": ai_insight.get("recommendation", "")
            })

if not final_races:
    fallback_horses = [
        {"num": 1, "name": "オオバンブルマイ", "jockey": "武豊", "odds": 17.1, "recent": "キーンランドC 3着", "score": 82.5, "mark": "▲ 単穴"},
        {"num": 2, "name": "トウシンマカオ", "jockey": "菅原明良", "odds": 9.6, "recent": "セントウルS 1着", "score": 85.0, "mark": "○ 対抗"},
        {"num": 5, "name": "ナムラクレア", "jockey": "横山武史", "odds": 8.2, "recent": "キーンランドC 2着", "score": 84.1, "mark": "☆ 穴"},
        {"num": 6, "name": "ママコチャ", "jockey": "川田将雅", "odds": 5.2, "recent": "セントウルS 2着", "score": 81.3, "mark": "-"},
        {"num": 12, "name": "サトノレーヴ", "jockey": "D.レーン", "odds": 3.0, "recent": "キーンランドC 1着", "score": 80.9, "mark": "△ 連下"},
        {"num": 13, "name": "ルガル", "jockey": "西村淳也", "odds": 28.5, "recent": "高松宮記念 10着", "score": 93.4, "mark": "◎ 本命"}
    ]
    ai_test = ask_gemini_prediction("11R スプリンターズS (G1)", "中山", fallback_horses)
    final_races = [
        {
            "raceId": "202606040811",
            "venue": "中山",
            "raceName": "11R スプリンターズS (G1) [ジェミ予想検証]",
            "startTime": "15:45",
            "isGraded": True,
            "horses": fallback_horses,
            "honmeiNum": 13,
            "aiSummary": ai_test.get("summary", ""),
            "aiBuy": ai_test.get("recommendation", "")
        }
    ]

# today.json の出力
output_data = {
    "updatedAt": now_str,
    "races": final_races
}
with open("data/today.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print("AI analysis completed.")
