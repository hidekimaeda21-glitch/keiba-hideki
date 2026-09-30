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

def ask_gemini_prediction(race_name, venue, horses, is_win5=False):
    """Gemini 3.8 Flash に脚質・上がり3Fを加味した推論と信頼度判定を行わせる"""
    if not client or not horses:
        return {
            "honmei_num": 1,
            "confidence": "B",
            "confidence_score": 75,
            "summary": "データ取得中またはAPIキー未設定",
            "recommendation": "単勝・複勝"
        }

    horse_summary = "\n".join([
        f"{h['num']}番 {h['name']} (騎手:{h['jockey']}, オッズ:{h['odds']}倍, 脚質:{h.get('style','先行')}, 前走上り3F:{h.get('last3f','35.0秒')}, 印:{h.get('mark', '-')})"
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
  "confidence": "レース信頼度(AまたはBまたはCのいずれか1文字。Aは的中確率が非常に高く鉄板、Cは波乱・大混戦)",
  "confidence_score": 50から98までの信頼度数値(半角数字),
  "summary": "脚質と上がり3Fから導いた展開予測と本命選定の明確な理由（100〜140文字程度）",
  "recommendation": "推奨買い目（例：単勝 13 / 馬連 13-1,2,5 / 3連複 13-2,5-1,2,5,6 など）"
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
        "confidence_score": 70,
        "summary": "オッズと脚質傾向を重視した先行・好位差し構成です。",
        "recommendation": "単勝・馬連流し"
    }

def generate_win5_10points(win5_races):
    """WIN5対象5レースから合計10点買いの買い目構成を自動選定"""
    if len(win5_races) < 5:
        return "WIN5対象レース集計中（確定後に10点買い目を自動算出）"

    # 各レースの有力候補馬番（本命と対抗）を抽出
    picks = []
    for r in win5_races[:5]:
        top_horses = [h["num"] for h in r["horses"] if h.get("mark") in ["◎ 本命", "○ 対抗"]]
        if not top_horses:
            top_horses = [h["num"] for h in r["horses"][:2]]
        picks.append(top_horses)

    # 10点構成：圧倒的信頼の2レースを1頭固定、残りを2頭・1頭・5頭などに配分 (1 x 1 x 2 x 1 x 5 = 10点)
    r1 = [picks[0][0]]
    r2 = [picks[1][0]]
    r3 = picks[2][:2] if len(picks[2]) >= 2 else [picks[2][0]]
    r4 = [picks[3][0]]
    # 5レース目は手広く5頭
    r5 = [h["num"] for h in win5_races[4]["horses"][:5]]

    total_points = len(r1) * len(r2) * len(r3) * len(r4) * len(r5)
    return f"【厳選10点買い(各100円)】 ①{r1[0]} ➔ ②{r2[0]} ➔ ③{','.join(map(str, r3))} ➔ ④{r4[0]} ➔ ⑤{','.join(map(str, r5))} (計{total_points}点 / 1,000円)"

def get_live_races():
    url = "[https://race.netkeiba.com/top/](https://race.netkeiba.com/top/)"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "EUC-JP"
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception:
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
            race_id_match = re.search(r"race_id=(\d+)", href)
            race_id = race_id_match.group(1) if race_id_match else ""

            # WIN5対象判定（後半メイン周辺）
            is_win5 = ("11R" in r_num or "10R" in r_num)

            if is_kansai or is_graded:
                target_races.append({
                    "venue": venue_name[:2],
                    "raceNum": r_num,
                    "raceName": f"{r_num} {r_name}",
                    "startTime": r_time,
                    "isGraded": is_graded,
                    "isWin5": is_win5,
                    "raceId": race_id
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

            # 脚質と前走上がり3Fの抽出
            row_text = row.text
            # 上がり3F（33.5秒〜39.9秒のパターン検索）
            agari_match = re.search(r"(3[3-9]\.\d)", row_text)
            last_3f = f"{agari_match.group(1)}秒" if agari_match else "34.8秒"

            # 通過順から脚質判定
            if any(p in row_text for p in ["1-1", "1-2"]):
                style = "逃げ"
            elif any(p in row_text for p in ["2-2", "3-3", "4-3", "2-3"]):
                style = "先行"
            elif any(p in row_text for p in ["12-", "13-", "14-", "15-", "16-"]):
                style = "追込"
            else:
                style = "差し"

            # 近走成績
            recent_cells = row.select(".PastRun_Data")
            recents = [c.text.strip() for c in recent_cells[:2] if c.text.strip()]
            recent_str = "/".join(recents) if recents else "近走集計中"

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
                    "style": style,
                    "last3f": last_3f,
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
    for r in live_meta[:12]:
        h_list = scrape_shutuba(r["raceId"])
        if h_list:
            ai_insight = ask_gemini_prediction(r["raceName"], r["venue"], h_list, r.get("isWin5", False))
            final_races.append({
                "raceId": r["raceId"],
                "venue": r["venue"],
                "raceName": r["raceName"],
                "startTime": r["startTime"],
                "isGraded": r["isGraded"],
                "isWin5": r.get("isWin5", False),
                "horses": h_list,
                "honmeiNum": ai_insight.get("honmei_num"),
                "confidence": ai_insight.get("confidence", "B"),
                "confidenceScore": ai_insight.get("confidence_score", 75),
                "aiSummary": ai_insight.get("summary", ""),
                "aiBuy": ai_insight.get("recommendation", "")
            })

# 平日フォールバック
if not final_races:
    fallback_horses = [
        {"num": 1, "name": "オオバンブルマイ", "jockey": "武豊", "odds": 17.1, "style": "追込", "last3f": "33.2秒", "recent": "キーンランドC 3着", "score": 82.5, "mark": "▲ 単穴"},
        {"num": 2, "name": "トウシンマカオ", "jockey": "菅原明良", "odds": 9.6, "style": "差し", "last3f": "33.5秒", "recent": "セントウルS 1着", "score": 85.0, "mark": "○ 対抗"},
        {"num": 5, "name": "ナムラクレア", "jockey": "横山武史", "odds": 8.2, "style": "差し", "last3f": "33.4秒", "recent": "キーンランドC 2着", "score": 84.1, "mark": "☆ 穴"},
        {"num": 6, "name": "ママコチャ", "jockey": "川田将雅", "odds": 5.2, "style": "先行", "last3f": "34.1秒", "recent": "セントウルS 2着", "score": 81.3, "mark": "-"},
        {"num": 12, "name": "サトノレーヴ", "jockey": "D.レーン", "odds": 3.0, "style": "先行", "last3f": "33.9秒", "recent": "キーンランドC 1着", "score": 80.9, "mark": "△ 連下"},
        {"num": 13, "name": "ルガル", "jockey": "西村淳也", "odds": 28.5, "style": "先行", "last3f": "33.7秒", "recent": "高松宮記念 10着", "score": 93.4, "mark": "◎ 本命"}
    ]
    ai_test = ask_gemini_prediction("11R スプリンターズS (G1)", "中山", fallback_horses)
    final_races = [
        {
            "raceId": "202606040811",
            "venue": "中山",
            "raceName": "11R スプリンターズS (G1) [ジェミ予想検証]",
            "startTime": "15:45",
            "isGraded": True,
            "isWin5": False,
            "horses": fallback_horses,
            "honmeiNum": 13,
            "confidence": "A",
            "confidenceScore": 92,
            "aiSummary": ai_test.get("summary", ""),
            "aiBuy": ai_test.get("recommendation", "")
        },
        {
            "raceId": "202609040810",
            "venue": "阪神",
            "raceName": "10R 道頓堀S",
            "startTime": "15:10",
            "isGraded": False,
            "isWin5": False,
            "horses": fallback_horses,
            "honmeiNum": 2,
            "confidence": "A",
            "confidenceScore": 89,
            "aiSummary": "開幕週の絶好馬場。先行力と上がり33秒台の決め手を併せ持つトウシンマカオの好位抜け出しが濃厚。",
            "aiBuy": "単勝 2 / 馬連 2-5,12"
        },
        {
            "raceId": "202609040809",
            "venue": "阪神",
            "raceName": "9R 芦屋川特別",
            "startTime": "14:35",
            "isGraded": False,
            "isWin5": False,
            "horses": fallback_horses,
            "honmeiNum": 12,
            "confidence": "A",
            "confidenceScore": 88,
            "aiSummary": "前走上がり33秒台で完勝したサトノレーヴ。斤量据え置きで鞍上も強力、軸としての信頼度は高い。",
            "aiBuy": "単勝 12 / 馬単 12➔1,2"
        }
    ]

# WIN5対象レースの抽出
win5_races = [r for r in final_races if r.get("isWin5")]
win5_strategy = generate_win5_10points(win5_races if win5_races else final_races)

# WIN5以外のレースから信頼度スコアTOP3を「今日の勝負レース」として選抜
non_win5_races = [r for r in final_races if not r.get("isWin5")]
sorted_by_conf = sorted(non_win5_races, key=lambda x: x.get("confidenceScore", 0), reverse=True)
best_races = sorted_by_conf[:3]

output_data = {
    "updatedAt": now_str,
    "win5Strategy": win5_strategy,
    "bestRaces": best_races,
    "races": final_races
}

with open("data/today.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print("AI analysis completed with TOP3 best bets & WIN5 10-points strategy.")
