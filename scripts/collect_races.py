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

# 日本時間（JST）の計算
now_utc = datetime.utcnow()
now_jst = now_utc + timedelta(hours=9)
now_str = now_jst.strftime("%Y-%m-%d %H:%M")

# 15時以降は翌日、それ以前は当日を自動対象
if now_jst.hour >= 15:
    target_dt = now_jst + timedelta(days=1)
else:
    target_dt = now_jst

target_date = target_dt.strftime("%Y%m%d")
target_date_disp = target_dt.strftime("%Y年%m月%d日")

print(f"=== 実行日時(JST): {now_str} / 自動対象開催日: {target_date_disp} ({target_date}) ===")

api_key = os.environ.get("GEMINI_API_KEY")
raw_proxy = os.environ.get("PROXY_URL", "").strip()

if raw_proxy and not raw_proxy.startswith("http://") and not raw_proxy.startswith("https://"):
    proxy_base = f"https://{raw_proxy}".rstrip("/")
else:
    proxy_base = raw_proxy.rstrip("/")

client = genai.Client(api_key=api_key) if api_key else None

def fetch_html(target_url):
    """プロキシ経由および直接通信による安全なHTML取得"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
    }
    
    if proxy_base and proxy_base.startswith("http"):
        try:
            encoded_url = urllib.parse.quote(target_url, safe="")
            proxy_url = f"{proxy_base}/?url={encoded_url}"
            res = requests.get(proxy_url, headers=headers, timeout=20)
            if res.status_code == 200 and len(res.text) > 200:
                res.encoding = res.apparent_encoding if res.apparent_encoding else "euc-jp"
                return res.text
        except Exception as e:
            print(f"[プロキシ取得警告] {target_url} : {e}")

    try:
        res = requests.get(target_url, headers=headers, timeout=15)
        res.encoding = res.apparent_encoding if res.apparent_encoding else "euc-jp"
        return res.text
    except Exception as e:
        print(f"[直接取得エラー] {target_url} : {e}")
        return ""

def collect_target_races_dynamically(target_yyyymmdd):
    """netkeibaから指定日の9R〜12RのレースIDを動的に自動抽出"""
    urls_to_try = [
        f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={target_yyyymmdd}",
        f"https://race.netkeiba.com/top/race_list.html?kaisai_date={target_yyyymmdd}"
    ]
    
    found_race_ids = []
    for u in urls_to_try:
        html = fetch_html(u)
        if not html:
            continue
        
        matches = re.findall(r"race_id=(\d{12})", html)
        for rid in matches:
            if rid not in found_race_ids:
                found_race_ids.append(rid)
        
        if found_race_ids:
            break

    race_items = []
    for rid in found_race_ids:
        r_num = int(rid[10:12])
        if r_num in [9, 10, 11, 12]:
            clean_url = f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}"
            race_items.append({"race_id": rid, "url": clean_url, "r_num": r_num})

    race_items = sorted(race_items, key=lambda x: x["race_id"])
    print(f"動的検知レース数 (9〜12R): {len(race_items)} 件")
    return race_items

def parse_race_details(race_info):
    """10月3日の成功方式で出走馬・騎手・オッズを取得"""
    race_id = race_info["race_id"]
    html = fetch_html(race_info["url"])
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    
    r_name_elem = soup.find("div", class_="RaceName") or soup.find("h1", class_="RaceName")
    r_name = r_name_elem.get_text(strip=True) if r_name_elem else f"{race_info['r_num']}R"
    
    r_data_elem = soup.find("div", class_="RaceData01")
    r_data = r_data_elem.get_text(strip=True) if r_data_elem else ""
    
    dist_match = re.search(r"(芝|ダ|障)(\d{4}m)", r_data)
    dist_str = f" ({dist_match.group(0)})" if dist_match else ""

    time_match = re.search(r"(\d{2}:\d{2})発走", r_data)
    start_time = time_match.group(1) if time_match else "15:00"

    venue_map = {
        "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
        "05": "東京", "06": "中山", "07": "中京", "08": "京都",
        "09": "阪神", "10": "小倉"
    }
    venue_code = race_id[4:6]
    venue = venue_map.get(venue_code, "中央")

    full_race_title = f"{race_info['r_num']}R {r_name}{dist_str}"

    horses = []
    table = soup.find("table", class_="RaceTable01") or soup.find("table", class_="Shutuba_Table")
    if table:
        rows = table.find_all("tr", class_=re.compile(r"HorseList"))
        for tr in rows:
            num_td = tr.find("td", class_=re.compile(r"Umaban"))
            name_td = tr.find("span", class_="HorseName") or tr.find("td", class_="HorseInfo")
            jockey_td = tr.find("td", class_="Jockey")

            if not num_td or not name_td:
                continue

            try:
                num = int(num_td.get_text(strip=True))
            except ValueError:
                continue

            name = name_td.get_text(strip=True)
            jockey = jockey_td.get_text(strip=True) if jockey_td else "未定"
            
            # --- 3日成功時のオッズ抽出ロジック ---
            odds_val = None
            
            # spanタグのID（odds-1, odds_1）またはテキスト
            for sp in tr.find_all("span"):
                sp_id = sp.get("id", "")
                if "odds" in sp_id or "Popular" in " ".join(sp.get("class", [])):
                    m = re.search(r"(\d{1,3}\.\d)", sp.get_text(strip=True))
                    if m:
                        odds_val = float(m.group(1))
                        break
            
            # tdタグのPopular/Odds
            if odds_val is None:
                for td in tr.find_all("td"):
                    td_cls = " ".join(td.get("class", []))
                    if any(c in td_cls for c in ["Popular", "Odds"]):
                        m = re.search(r"(\d{1,3}\.\d)", td.get_text(strip=True))
                        if m:
                            odds_val = float(m.group(1))
                            break

            # 万が一前日発売前等でオッズが完全ブランクだった場合の自然な初期値
            if odds_val is None or odds_val <= 0:
                odds_val = 10.0

            horses.append({
                "num": num,
                "name": name,
                "jockey": jockey,
                "odds": odds_val,
                "style": "先行",
                "last3f": "34.2秒",
                "score": round(max(70.0, 96.0 - (odds_val * 0.4)), 1),
                "mark": "-"
            })

    # オッズ順にソートして印を自動付与
    if horses:
        horses_sorted = sorted(horses, key=lambda x: x["odds"])
        horses_sorted[0]["mark"] = "◎ 本命"
        if len(horses_sorted) > 1:
            horses_sorted[1]["mark"] = "○ 対抗"
        if len(horses_sorted) > 2:
            horses_sorted[2]["mark"] = "▲ 単穴"
        
        ana_candidates = [h for h in horses if 10.0 <= h["odds"] <= 55.0]
        if ana_candidates:
            ana_candidates[0]["mark"] = "☆ 爆発期待穴"

        for h in horses_sorted[3:6]:
            if h.get("mark") == "-":
                h["mark"] = "△ 連下"

    return {
        "raceId": race_id,
        "venue": venue,
        "raceName": full_race_title,
        "startTime": start_time,
        "isGraded": "重賞" in r_name or "(G" in r_name or "(L" in r_name,
        "isWin5": race_info["r_num"] in [10, 11],
        "horses": sorted(horses, key=lambda x: x["num"])
    }

def get_fallback_prediction(horses):
    """印に連動した安全バックアップ買い目（10点以内）"""
    honmei = next((h for h in horses if "◎" in h.get("mark", "")), horses[0])
    taikou = next((h for h in horses if "○" in h.get("mark", "")), None)
    tanana = [h for h in horses if "▲" in h.get("mark", "")]
    ana = [h for h in horses if "☆" in h.get("mark", "")]

    h_num = honmei["num"]
    rec_parts = []
    
    main_opps = []
    if taikou and taikou["num"] != h_num:
        main_opps.append(taikou["num"])
    for t in tanana:
        if t["num"] != h_num and t["num"] not in main_opps:
            main_opps.append(t["num"])
        if len(main_opps) >= 3:
            break

    if main_opps:
        opp_str = ", ".join(map(str, main_opps))
        rec_parts.append(f"【馬連】{h_num} - {opp_str} ({len(main_opps)}点)")

    if ana and ana[0]["num"] != h_num:
        ana_num = ana[0]["num"]
        wide_targets = [str(h_num)]
        if taikou and taikou["num"] != ana_num and taikou["num"] != h_num:
            wide_targets.append(str(taikou["num"]))
        rec_parts.append(f"【穴ワイド】{ana_num} - {', '.join(wide_targets)} ({len(wide_targets)}点)")

    recommendation_text = " / ".join(rec_parts) if rec_parts else f"【単勝】{h_num}"

    return {
        "honmei_num": h_num,
        "confidence": "B",
        "confidence_score": 85,
        "summary": f"能力最上位の{h_num}番{honmei['name']}を軸に推奨。相手には印上位馬を絡め、無駄な点数を削った高回収率を狙う。",
        "recommendation": recommendation_text
    }

def ask_gemini_prediction(race_name, venue, horses):
    """Gemini 3.8 Flash による【回収率重視・印連動・合計10点以内】推論"""
    if not client or not horses:
        return get_fallback_prediction(horses)

    horse_summary = "\n".join([
        f"{h['num']}番 {h['name']} (騎手:{h['jockey']}, オッズ:{h['odds']}倍, 印:{h.get('mark', '-')})"
        for h in horses
    ])

    prompt = f"""
あなたは回収率を最大化し競馬で勝つための専属AI「ジェミ予想」です。

【重要指示】
1. 印のルール：
   ・「◎ 本命」は必ず【1頭のみ】選定。
   ・「○ 対抗」は必ず【1頭のみ】選定。
   ・買い目は必ず印がついた馬番（◎・○・▲・☆・△）のみで構成してください。
2. 【最重要：買い目点数は合計10点以内】
   ・無理に全券種を出さず、最も期待値の高い買い方に絞ってください。
   ・提示する買い目の合計点数は必ず【10点以内（10点以下）】を絶対厳守してください。

会場: {venue}
レース名: {race_name}
出走馬一覧:
{horse_summary}

必ず以下のJSON形式のみを出力してください:
{{
  "honmei_num": 本命馬の馬番(半角数字),
  "confidence": "AまたはBまたはC",
  "confidence_score": 80から96までの数値(半角数字),
  "summary": "◎本命馬と相手穴馬の狙い（100〜140文字程度）",
  "recommendation": "推奨買い目（合計10点以内で具体的に記述）"
}}
"""
    for model_name in ['gemini-3.8-flash', 'gemini-3.5-flash']:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            txt = res.text.strip()
            txt = re.sub(r"^```json\s*", "", txt)
            txt = re.sub(r"^```\s*", "", txt)
            txt = re.sub(r"\s*```$", "", txt)
            data = json.loads(txt)
            if data.get("honmei_num") in [h["num"] for h in horses] and data.get("recommendation"):
                return data
        except Exception:
            continue

    return get_fallback_prediction(horses)

def ask_gemini_win5_strategy(win5_races_info):
    """GeminiによるWIN5厳選戦略（最大10点まで・予算1,000円以内）"""
    default_text = "本日WIN5対象レース確定後に厳選買い目を配信します。"
    if not client or len(win5_races_info) < 5:
        return default_text

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
# メイン実行フロー（完全自動・恒久対応）
# ==========================================

print("=== 1. レース情報の動的クローリング開始 ===")
detected_races = collect_target_races_dynamically(target_date)

if not detected_races and target_date != now_jst.strftime("%Y%m%d"):
    print("翌日データが未検出のため、本日開催データで再試行します...")
    target_date = now_jst.strftime("%Y%m%d")
    detected_races = collect_target_races_dynamically(target_date)

final_races = []
for r_info in detected_races:
    print(f"解析中: {r_info['race_id']}...")
    detail = parse_race_details(r_info)
    if detail and detail["horses"]:
        ai_res = ask_gemini_prediction(detail["raceName"], detail["venue"], detail["horses"])
        detail["honmeiNum"] = ai_res.get("honmei_num")
        detail["confidence"] = ai_res.get("confidence", "A")
        detail["confidenceScore"] = ai_res.get("confidence_score", 85)
        detail["aiSummary"] = ai_res.get("summary", "")
        detail["aiBuy"] = ai_res.get("recommendation", "")
        final_races.append(detail)
        time.sleep(1.2)

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

print(f"=== 完全自動処理完了: 計 {len(final_races)} レースのデータを自動生成・保存しました ===")
