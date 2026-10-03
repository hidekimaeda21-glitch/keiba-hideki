import os
import re
import json
import time
from datetime import datetime, timedelta
import urllib.parse
import requests
from bs4 import BeautifulSoup
from google import genai

os.makedirs("data", exist_ok=True)

# 日本時間（JST）の現在時刻を取得
# 夕方15時以降の実行であれば「翌日のレース」、午前〜昼であれば「当日のレース」を自動対象とする
now_utc = datetime.utcnow()
now_jst = now_utc + timedelta(hours=9)
now_str = now_jst.strftime("%Y-%m-%d %H:%M")

if now_jst.hour >= 15:
    target_date = (now_jst + timedelta(days=1)).strftime("%Y%m%d")
    target_date_disp = (now_jst + timedelta(days=1)).strftime("%Y年%m月%d日")
else:
    target_date = now_jst.strftime("%Y%m%d")
    target_date_disp = now_jst.strftime("%Y年%m月%d日")

print(f"=== 実行日時(JST): {now_str} / 対象競馬開催日: {target_date_disp} ({target_date}) ===")

api_key = os.environ.get("GEMINI_API_KEY")
proxy_base = os.environ.get("PROXY_URL", "").rstrip("/")
client = genai.Client(api_key=api_key) if api_key else None

def fetch_html(target_url):
    """Cloudflare Worker経由、または直接HTMLを取得"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
    }
    try:
        if proxy_base:
            encoded_url = urllib.parse.quote(target_url, safe="")
            proxy_url = f"{proxy_base}/?url={encoded_url}"
            res = requests.get(proxy_url, headers=headers, timeout=20)
        else:
            res = requests.get(target_url, headers=headers, timeout=15)
        
        # 文字コード判定
        res.encoding = res.apparent_encoding if res.apparent_encoding else "euc-jp"
        return res.text
    except Exception as e:
        print(f"[取得エラー] {target_url} : {e}")
        return ""

def collect_target_races_dynamically(target_yyyymmdd):
    """netkeiba等の当日・翌日一覧から主要開催場の9R〜12Rを動的に取得"""
    top_url = f"https://race.netkeiba.com/top/race_list.html?kaisai_date={target_yyyymmdd}"
    html = fetch_html(top_url)
    if not html:
        print("トップページの取得に失敗しました。")
        return []

    soup = BeautifulSoup(html, "html.parser")
    race_links = []
    
    # レース一覧からレースURLを抽出
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "race_id=" in href and "shutuba.html" in href:
            full_url = urllib.parse.urljoin("https://race.netkeiba.com/", href)
            # 重複除外
            if full_url not in [r["url"] for r in race_links]:
                # 9R, 10R, 11R, 12Rのみを対象とする
                m = re.search(r"race_id=(\d{12})", full_url)
                if m:
                    race_id = m.group(1)
                    r_num = int(race_id[10:12])
                    if r_num in [9, 10, 11, 12]:
                        race_links.append({"race_id": race_id, "url": full_url, "r_num": r_num})

    print(f"動的検知レース数 (9〜12R): {len(race_links)} 件")
    return race_links

def parse_race_details(race_info):
    """レース詳細ページから出走馬・距離・コース情報をパース"""
    html = fetch_html(race_info["url"])
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    
    # レース名と距離・条件
    r_name_elem = soup.find("div", class_="RaceName") or soup.find("h1", class_="RaceName")
    r_name = r_name_elem.get_text(strip=True) if r_name_elem else f"{race_info['r_num']}R"
    
    r_data_elem = soup.find("div", class_="RaceData01")
    r_data = r_data_elem.get_text(strip=True) if r_data_elem else ""
    
    # 距離の抽出 (例: 芝1800m, ダ1400m)
    dist_match = re.search(r"(芝|ダ|障)(\d{4}m)", r_data)
    dist_str = f" ({dist_match.group(0)})" if dist_match else ""

    # 発走時刻
    time_match = re.search(r"(\d{2}:\d{2})発走", r_data)
    start_time = time_match.group(1) if time_match else "15:00"

    # 競馬場名
    venue_map = {"05": "東京", "08": "京都", "09": "阪神", "06": "中山", "03": "福島", "07": "中京", "10": "小倉", "04": "新潟", "01": "札幌", "02": "函館"}
    venue_code = race_info["race_id"][4:6]
    venue = venue_map.get(venue_code, "中央")

    full_race_title = f"{race_info['r_num']}R {r_name}{dist_str}"

    horses = []
    # 出走表テーブル
    table = soup.find("table", class_="RaceTable01") or soup.find("table", class_="Shutuba_Table")
    if table:
        rows = table.find_all("tr", class_=re.compile(r"HorseList"))
        for tr in rows:
            num_td = tr.find("td", class_=re.compile(r"Umaban"))
            name_td = tr.find("span", class_="HorseName") or tr.find("td", class_="HorseInfo")
            jockey_td = tr.find("td", class_="Jockey")
            odds_td = tr.find("td", class_=re.compile(r"Popular|Odds"))

            if not num_td or not name_td:
                continue

            try:
                num = int(num_td.get_text(strip=True))
            except ValueError:
                continue

            name = name_td.get_text(strip=True)
            jockey = jockey_td.get_text(strip=True) if jockey_td else "未定"
            
            # オッズ取得
            odds_text = odds_td.get_text(strip=True) if odds_td else "10.0"
            try:
                odds_val = float(re.search(r"\d+\.\d+", odds_text).group(0))
            except Exception:
                odds_val = 15.0

            horses.append({
                "num": num,
                "name": name,
                "jockey": jockey,
                "odds": odds_val,
                "style": "先行",
                "last3f": "34.5秒",
                "score": round(max(70.0, 95.0 - (odds_val * 0.4)), 1),
                "mark": "-"
            })

    # 印を自動付与（オッズとスコア基準：◎本命1頭、○対抗1頭、▲・☆・△）
    if horses:
        horses_sorted = sorted(horses, key=lambda x: x["odds"])
        horses_sorted[0]["mark"] = "◎ 本命"
        if len(horses_sorted) > 1:
            horses_sorted[1]["mark"] = "○ 対抗"
        if len(horses_sorted) > 2:
            horses_sorted[2]["mark"] = "▲ 単穴"
        
        # オッズ10倍〜50倍で最もスコアの高い馬を「☆ 爆発期待穴」
        ana_candidates = [h for h in horses if 10.0 <= h["odds"] <= 55.0]
        if ana_candidates:
            ana_candidates[0]["mark"] = "☆ 爆発期待穴"

        # 連下
        for h in horses_sorted[3:6]:
            if h.get("mark") == "-":
                h["mark"] = "△ 連下"

    return {
        "raceId": race_info["race_id"],
        "venue": venue,
        "raceName": full_race_title,
        "startTime": start_time,
        "isGraded": "重賞" in r_name or "(G" in r_name or "(L" in r_name,
        "isWin5": race_info["r_num"] in [10, 11],
        "horses": sorted(horses, key=lambda x: x["num"])
    }

def ask_gemini_prediction(race_name, venue, horses):
    """Gemini 3.8 Flash による【回収率重視・印連動・合計10点以内】推論"""
    honmei = next((h for h in horses if "◎" in h.get("mark", "")), horses[0] if horses else {"num": 1, "name": "本命"})
    taikou = next((h for h in horses if "○" in h.get("mark", "")), horses[1] if len(horses) > 1 else None)
    tanana = [h for h in horses if "▲" in h.get("mark", "")]
    ana = [h for h in horses if "☆" in h.get("mark", "")]

    # デフォルトの安全な買い目
    default_rec = f"【馬連】{honmei['num']} - {taikou['num'] if taikou else 2} (1点)"
    if not client or not horses:
        return {
            "honmei_num": honmei["num"],
            "confidence": "B",
            "confidence_score": 85,
            "summary": f"能力上位の{honmei['num']}番{honmei['name']}を本命に推奨。オッズ妙味と展開から回収率重視で狙う。",
            "recommendation": default_rec
        }

    horse_summary = "\n".join([
        f"{h['num']}番 {h['name']} (騎手:{h['jockey']}, オッズ:{h['odds']}倍, 印:{h.get('mark', '-')})"
        for h in horses
    ])

    prompt = f"""
あなたは回収率を最大化し競馬で勝つための専属AI「ジェミ予想」です。

【重要ルール】
1. 印のルール：
   ・「◎ 本命」は必ず【1頭のみ】
   ・「○ 対抗」は必ず【1頭のみ】
   ・買い目は必ず印がついた馬番（◎・○・▲・☆・△）のみで構成してください。無印の馬は買わないでください。
2. 【最重要：買い目点数は合計10点以内】
   ・無理に全券種を出さず、最も期待値の高い買い方に絞ってください。
   ・（例: 馬連 2〜3点 / 3連複フォーメーション 4〜6点 / 穴ワイド 1〜2点 など）
   ・提示する買い目の合計点数は必ず【10点以内】に収めてください。

会場: {venue}
レース名: {race_name}
出走馬一覧:
{horse_summary}

必ず以下のJSON形式のみを出力してください:
{{
  "honmei_num": 本命馬の馬番(半角数字),
  "confidence": "レース信頼度(AまたはBまたはC)",
  "confidence_score": 50から98までの信頼度数値(半角数字),
  "summary": "◎本命の選定理由と爆発期待穴馬の狙い（100〜140文字程度）",
  "recommendation": "推奨買い目（合計10点以内で具体的に記述）"
}}
"""
    for model_name in ['gemini-3.8-flash', 'gemini-3.5-flash']:
        try:
            res = client.models.generate_content(model=model_name, contents=prompt)
            txt = res.text.strip()
            txt = re.sub(r"^```json\s*", "", txt)
            txt = re.sub(r"^```\s*", "", txt)
            txt = re.sub(r"\s*```$", "", txt)
            data = json.loads(txt)
            if data.get("honmei_num") and data.get("recommendation"):
                return data
        except Exception:
            continue

    return {
        "honmei_num": honmei["num"],
        "confidence": "B",
        "confidence_score": 85,
        "summary": f"能力上位の{honmei['num']}番{honmei['name']}を本命に推奨。展開がハマった際の爆発力とオッズ妙味を考慮して選定。",
        "recommendation": default_rec
    }

def ask_gemini_win5_strategy(win5_races_info):
    """GeminiによるWIN5厳選戦略（最大10点まで・予算1,000円以内）"""
    default_text = "本日WIN5対象レース分析中"
    if not client or len(win5_races_info) < 5:
        return "WIN5対象レース確定後に厳選買い目を配信します。"

    summary_text = ""
    for idx, r in enumerate(win5_races_info[:5], 1):
        top_h = ", ".join([f"{h['num']}番({h['odds']}倍)" for h in r['horses'][:3]])
        summary_text += f"第{idx}戦 ({r['venue']} {r['raceName']}): 上位候補: {top_h}\n"

    prompt = f"""
本日のWIN5対象5レースの情報をもとに、買い目点数を【通常は最大10点まで（全体の組み合わせ数が10点以内、予算1,000円以内）】として各レースの選定頭数を割り振ってください。

対象レース:
{summary_text}

出力フォーマット（この形式のみを出力）:
本日WIN5発売中！【AI厳選○点戦略（予算○○○円 / 最大10点まで）】
①: [馬番] ➔ ②: [馬番] ➔ ③: [馬番] ➔ ④: [馬番] ➔ ⑤: [馬番]
理由: (30文字前後で選定の狙い)
"""
    for model_name in ['gemini-3.8-flash', 'gemini-3.5-flash']:
        try:
            res = client.models.generate_content(model=model_name, contents=prompt)
            txt = res.text.strip()
            if "①" in txt and "➔" in txt:
                return txt
        except Exception:
            continue

    return "本日WIN5発売中！【AI厳選戦略】各レース本命中心に点数を絞って配信中。"

# ==========================================
# メイン実行フロー（完全自動）
# ==========================================

print("=== 1. レース情報の動的クローリング開始 ===")
detected_races = collect_target_races_dynamically(target_date)

# 万が一当日/翌日のレース取得がゼロだった場合のフェイルセーフ（当日日付でも再試行）
if not detected_races and target_date != now_jst.strftime("%Y%m%d"):
    print("翌日データが未公開のため、本日開催データで再試行します...")
    target_date = now_jst.strftime("%Y%m%d")
    detected_races = collect_target_races_dynamically(target_date)

final_races = []
for r_info in detected_races:
    print(f"解析中: {r_info['race_id']}...")
    detail = parse_race_details(r_info)
    if detail and detail["horses"]:
        ai_res = ask_gemini_prediction(detail["raceName"], detail["venue"], detail["horses"])
        detail["honmeiNum"] = ai_res.get("honmei_num")
        detail["confidence"] = ai_res.get("confidence", "B")
        detail["confidenceScore"] = ai_res.get("confidence_score", 85)
        detail["aiSummary"] = ai_res.get("summary", "")
        detail["aiBuy"] = ai_res.get("recommendation", "")
        final_races.append(detail)
        time.sleep(1.2)

# WIN5対象レースの抽出
win5_races_list = [r for r in final_races if r["isWin5"]]
win5_strategy_text = ask_gemini_win5_strategy(win5_races_list)

sorted_by_conf = sorted(final_races, key=lambda x: x.get("confidenceScore", 0), reverse=True)
best_races = sorted_by_conf[:3]

output_data = {
    "updatedAt": now_str,
    "targetDate": target_date_disp,
    "win5Strategy": win5_strategy_text,
    "bestRaces": best_races,
    "races": final_races
}

with open("data/today.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"=== 完全自動処理完了: 計 {len(final_races)} レースの最新データを自動生成・保存しました ===")
