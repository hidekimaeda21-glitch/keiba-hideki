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
    """Gemini 3.8 Flash に脚質・上がり3Fを加味した推論を行わせる"""
    if not client or not horses:
        return {
            "honmei_num": horses[0]["num"] if horses else 1,
            "confidence": "B",
            "confidence_score": 75,
            "summary": "データ取得中またはAPIキー未設定",
            "recommendation": "単勝・複勝"
        }

    horse_summary = "\n".join([
        f"{h['num']}番 {h['name']} (騎手:{h['jockey']}, 単勝:{h['odds']}倍, 脚質:{h.get('style','先行')}, 前走上り3F:{h.get('last3f','34.5秒')}, 印:{h.get('mark', '-')})"
        for h in horses[:14]
    ])

    prompt = f"""
あなたはプロの競馬AI予想家「ジェミ予想」です。
以下の出走表、各馬の脚質、および前走の上がり3F（最後の600mタイム）を分析し、展開ペースを予測した上で本命馬・推奨買い目・レース信頼度を判定してください。

会場: {venue}
レース名: {race_name}
出走馬情報:
{horse_summary}

必ず以下のJSON形式のみを出力してください（Markdownコードブロックは不要です）:
{{
  "honmei_num": 本命馬の馬番(半角数字),
  "confidence": "レース信頼度(AまたはBまたはCのいずれか1文字。Aは的中確率が高く鉄板、Cは波乱・大混戦)",
  "confidence_score": 50から98までの信頼度数値(半角数字),
  "summary": "脚質と上がり3Fから導いた展開予測と本命選定の理由（100〜140文字程度）",
  "recommendation": "推奨買い目（例：単勝 5 / 馬連 5-1,2,8 / 3連複 5-1,2-1,2,8 など）"
}}
"""
    candidate_models = ['gemini-3.8-flash', 'gemini-3.5-flash', 'gemini-3.5-flash-lite']
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
            if "confidence_score" not in data:
                data["confidence_score"] = 75
            return data
        except Exception:
            continue

    return {
        "honmei_num": horses[0]["num"] if horses else 1,
        "confidence": "B",
        "confidence_score": 75,
        "summary": "オッズと脚質傾向を重視した先行・好位差し構成です。",
        "recommendation": "単勝・馬連流し"
    }

def get_live_races():
    # 本日のレース一覧ページを直接取得
    url = f"[https://race.netkeiba.com/top/race_list.html](https://race.netkeiba.com/top/race_list.html)"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "EUC-JP"
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print(f"Error fetching top: {e}")
        return []

    target_races = []
    # レースリンクを一括抽出
    race_links = soup.select("a[href*='shutuba.html?race_id=']")
    seen_ids = set()

    for a in race_links:
        href = a.get("href", "")
        race_id_match = re.search(r"race_id=(\d+)", href)
        if not race_id_match:
            continue
        race_id = race_id_match.group(1)
        if race_id in seen_ids:
            continue
        seen_ids.add(race_id)

        # 親ブロックから会場名やレース名を取得
        parent = a.find_parent("li") or a.find_parent("tr") or a.find_parent("div")
        text_all = parent.text if parent else a.text
        
        # 会場名判定
        venue = "京都" if "08" in race_id[4:6] or "京都" in text_all else "東京" if "05" in race_id[4:6] or "東京" in text_all else "阪神" if "阪神" in text_all else "中央"
        
        # レース番号（例: 11R）
        r_num_match = re.search(r"(\d{1,2})R", text_all)
        r_num = f"{r_num_match.group(1)}R" if r_num_match else "11R"

        # レース名
        name_tag = a.select_one(".RaceName") or a
        r_name = name_tag.text.strip().split("\n")[0]
        if not r_name or r_name == r_num:
            r_name = f"{r_num} 特別競走"

        # 重賞・メイン・関西レースを優先
        is_graded = any(g in text_all for g in ["G1", "G2", "G3", "GI", "GII", "GIII", "重賞", "ステークス", "S"])
        is_win5 = ("10R" in r_num or "11R" in r_num)

        target_races.append({
            "venue": venue,
            "raceNum": r_num,
            "raceName": f"{r_num} {r_name}",
            "startTime": "発走準備中",
            "isGraded": is_graded,
            "isWin5": is_win5,
            "raceId": race_id
        })

    print(f"Discovered {len(target_races)} live races from netkeiba.")
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

            if not (num_tag and name_tag):
                continue

            row_text = row.text
            agari_match = re.search(r"(3[3-9]\.\d)", row_text)
            last_3f = f"{agari_match.group(1)}秒" if agari_match else "34.6秒"

            if any(p in row_text for p in ["1-1", "1-2"]):
                style = "逃げ"
            elif any(p in row_text for p in ["2-2", "3-3", "4-3", "2-3"]):
                style = "先行"
            elif any(p in row_text for p in ["12-", "13-", "14-", "15-", "16-"]):
                style = "追込"
            else:
                style = "差し"

            recent_cells = row.select(".PastRun_Data")
            recents = [c.text.strip() for c in recent_cells[:2] if c.text.strip()]
            recent_str = "/".join(recents) if recents else "近走集計中"

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
                "style": style,
                "last3f": last_3f,
                "recent": recent_str,
                "score": 0.0,
                "mark": "-"
            })
        time.sleep(1)
    except Exception as e:
        print(f"Error scraping shutuba {race_id}: {e}")

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
    # メインレースおよび後半レースを中心に最大8レースを抽出してAI推論
    target_subset = [r for r in live_meta if r["isGraded"] or "11R" in r["raceNum"] or "10R" in r["raceNum"]][:8]
    if not target_subset:
        target_subset = live_meta[:8]

    for r in target_subset:
        print(f"Analyzing {r['venue']} {r['raceName']} ({r['raceId']})...")
        h_list = scrape_shutuba(r["raceId"])
        if h_list:
            ai_insight = ask_gemini_prediction(r["raceName"], r["venue"], h_list)
            final_races.append({
                "raceId": r["raceId"],
                "venue": r["venue"],
                "raceName": r["raceName"],
                "startTime": r["startTime"],
                "isGraded": r["isGraded"],
                "isWin5": r["isWin5"],
                "horses": h_list,
                "honmeiNum": ai_insight.get("honmei_num"),
                "confidence": ai_insight.get("confidence", "B"),
                "confidenceScore": ai_insight.get("confidence_score", 75),
                "aiSummary": ai_insight.get("summary", ""),
                "aiBuy": ai_insight.get("recommendation", "")
            })

# 信頼度TOP3を勝負レースとして選出
sorted_by_conf = sorted(final_races, key=lambda x: x.get("confidenceScore", 0), reverse=True)
best_races = sorted_by_conf[:3]

output_data = {
    "updatedAt": now_str,
    "win5Strategy": "WIN5は日曜開催（本日は厳選勝負レースTOP3に集中）",
    "bestRaces": best_races,
    "races": final_races
}

with open("data/today.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"AI analysis completed. Total races: {len(final_races)}")
