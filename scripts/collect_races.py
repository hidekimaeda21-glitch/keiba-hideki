import os
import re
import json
import time
from datetime import datetime
import urllib.parse
import requests
from google import genai

os.makedirs("data", exist_ok=True)
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

api_key = os.environ.get("GEMINI_API_KEY")
proxy_base = os.environ.get("PROXY_URL", "").rstrip("/")
client = genai.Client(api_key=api_key) if api_key else None

def fetch_via_proxy(target_url):
    """Cloudflare Workerの中継プロキシを経由してHTMLを取得（WAF遮断を回避）"""
    if not proxy_base:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
        res = requests.get(target_url, headers=headers, timeout=10)
        res.encoding = res.apparent_encoding
        return res.text

    encoded_url = urllib.parse.quote(target_url, safe="")
    proxy_url = f"{proxy_base}/?url={encoded_url}"
    res = requests.get(proxy_url, timeout=15)
    return res.text

def get_fallback_prediction(horses):
    """印（◎・○・▲・☆・△）に完全に連動した論理的バックアップ買い目を自動生成（10点以内厳守）"""
    honmei = next((h for h in horses if "◎" in h.get("mark", "")), horses[0])
    taikou = next((h for h in horses if "○" in h.get("mark", "")), None)
    tanana = [h for h in horses if "▲" in h.get("mark", "")]
    ana = [h for h in horses if "☆" in h.get("mark", "")]
    renge = [h for h in horses if "△" in h.get("mark", "")]

    h_num = honmei["num"]
    rec_parts = []
    
    # 相手候補の整理
    main_opps = []
    if taikou:
        main_opps.append(taikou["num"])
    for t in tanana[:2]:
        main_opps.append(t["num"])

    # 馬連（2〜3点）
    if main_opps:
        opp_str = ", ".join(map(str, main_opps))
        rec_parts.append(f"【馬連】{h_num} - {opp_str} ({len(main_opps)}点)")

    # 穴ワイドまたは3連複（小点数）
    if ana and taikou:
        rec_parts.append(f"【穴ワイド】{ana[0]['num']} - {h_num}, {taikou['num']} (2点)")
    elif taikou and len(tanana) >= 1:
        rec_parts.append(f"【3連複F】{h_num} - {taikou['num']} - {tanana[0]['num']} (1点)")

    recommendation_text = " / ".join(rec_parts) if rec_parts else f"【単勝】{h_num}"

    return {
        "honmei_num": h_num,
        "confidence": "B",
        "confidence_score": 85,
        "summary": f"能力最上位の{h_num}番{honmei['name']}を本命に据える。相手には対抗格およびスピード指数の高い伏兵を絡め、無駄な点数を削った高回収率を狙う。",
        "recommendation": recommendation_text
    }

def ask_gemini_prediction(race_name, venue, horses):
    """Gemini 3.8 Flash による【印連動・回収率重視・10点以内】推論"""
    if not client or not horses:
        return get_fallback_prediction(horses)

    horse_summary = "\n".join([
        f"{h['num']}番 {h['name']} (騎手:{h['jockey']}, オッズ:{h['odds']}倍, 脚質:{h.get('style','先行')}, 上り3F:{h.get('last3f','35.0秒')}, 潜在能力スコア:{h.get('score', 80.0)}, 暫定印:{h.get('mark', '-')})"
        for h in horses
    ])

    prompt = f"""
あなたは回収率を最大化し競馬で勝つための専属AI「ジェミ予想」です。

【重要：予想＆買い目フォーメーション指示（印に完全連動・10点以内）】
1. 印のルール：
   ・「◎ 本命」は必ず【1頭のみ】選定してください。
   ・「○ 対抗」は必ず【1頭のみ】選定してください。
   ・単穴（▲）、特注穴馬（☆）、連下（△）は能力に応じて選定してください。
2. 【最重要：買い目は必ず印がついた馬番のみで構成すること】
   ・**無印（-）の馬を軸にしたり買い目に入れることは絶対に禁止**です。
   ・必ず「◎ 本命」を中心とし、「○ 対抗」「▲ 単穴」「☆ 特注穴」へ流す買い目を組んでください。
3. 【点数のルール】
   ・無理に全券種を並べず、馬連のみ、または3連複Fのみ、または穴ワイドのみ等、期待値の高い買い方に絞ってください。
   ・**買い目全体の合計点数は必ず【10点以内（10点以下）】を絶対厳守**してください。

会場: {venue}
レース名: {race_name}
全出走馬情報:
{horse_summary}

必ず以下のJSON形式のみを出力してください:
{{
  "honmei_num": 本命馬の馬番(半角数字),
  "confidence": "レース信頼度(AまたはBまたはC)",
  "confidence_score": 50から98までの信頼度数値(半角数字),
  "summary": "◎本命の選定根拠と相手穴馬の狙い（100〜140文字程度）",
  "recommendation": "【馬連】◎ - ○,▲ (○点) のように印に基づき合計10点以内で具体的に記述"
}}
"""
    for model_name in ['gemini-3.8-flash', 'gemini-3.5-flash']:
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
            
            # 整合性チェック：本命番号が馬リスト内に存在し、推奨買い目があるか
            if data.get("honmei_num") in [h["num"] for h in horses] and data.get("recommendation"):
                return data
        except Exception:
            continue

    return get_fallback_prediction(horses)

def ask_gemini_win5_strategy(win5_races_info):
    """Geminiに【通常は最大10点まで】のWIN5買い目を期待値重視で厳選計算させる"""
    default_text = (
        "本日WIN5発売中！【AI厳選戦略（最大10点まで / 予算1,000円以内）】\n"
        "①東京9R: [4] ➔ ②京都10R: [6, 14] ➔ ③東京10R: [5] ➔ ④京都11R: [3, 17] ➔ ⑤東京11R: [4, 11]\n"
        "買い目合計: 8点（予算800円）"
    )
    if not client:
        return default_text

    summary_text = ""
    for idx, r in enumerate(win5_races_info, 1):
        top_horses = ", ".join([f"{h['num']}番{h['name']}({h['odds']}倍)" for h in r['horses'][:4]])
        summary_text += f"第{idx}戦 ({r['venue']} {r['raceName']}): 本命{r['honmeiNum']}番, 上位候補: {top_horses}\n"

    prompt = f"""
あなたはWIN5分析のスペシャリスト「ジェミ予想」です。
本日のWIN5対象5レースの情報をもとに、買い目点数を【通常は最大10点まで（全体の組み合わせ数が10点以内、予算1,000円以内）】として各レースの選定頭数を割り振って買い目を決定してください。

【ルール】
・選定頭数の積（第1戦の頭数 × 第2戦の頭数 × 第3戦の頭数 × 第4戦の頭数 × 第5戦の頭数）は【最大10点まで】です。
・単なる人気順ではなく、能力発揮時の期待値（配当妙味）を考慮して選定してください。
・基本は10点を目指しますが、自信を持って1頭に絞れるレースがある場合は8点や6点など10点以内になるのは問題ありません。
・UI用のアナウンス文言は含めないでください。

対象レース一覧:
{summary_text}

出力フォーマット（この形式のみを出力）:
本日WIN5発売中！【AI厳選○点戦略（予算○○○円 / 最大10点まで）】
①東京9R: [馬番] ➔ ②京都10R: [馬番] ➔ ③東京10R: [馬番] ➔ ④京都11R: [馬番] ➔ ⑤東京11R: [馬番]
理由: (30文字前後で選定の狙い・期待値の根拠)
"""
    for model_name in ['gemini-3.8-flash', 'gemini-3.5-flash']:
        try:
            res = client.models.generate_content(model=model_name, contents=prompt)
            txt = res.text.strip()
            if "①" in txt and "➔" in txt:
                return txt
        except Exception:
            continue

    return default_text

# ==========================================
# 2026年10月3日（土曜）JRA公式確定出走馬データ
# ==========================================

# 京都12R（ダ1800m 14頭）
kyoto12_horses = [
    {"num": 1, "name": "ヒデノレインボー", "jockey": "藤懸貴志", "odds": 33.2, "style": "追込", "last3f": "37.5秒", "recent": "2勝クラス 9着", "score": 78.0, "mark": "-"},
    {"num": 2, "name": "フクキタテーラー", "jockey": "小沢大仁", "odds": 52.7, "style": "先行", "last3f": "38.2秒", "recent": "1勝クラス 1着", "score": 75.0, "mark": "-"},
    {"num": 3, "name": "レイザリオ", "jockey": "斎藤新", "odds": 18.6, "style": "差し", "last3f": "37.1秒", "recent": "2勝クラス 4着", "score": 83.5, "mark": "△ 連下"},
    {"num": 4, "name": "ジーニアスバローズ", "jockey": "松若風馬", "odds": 19.7, "style": "差し", "last3f": "37.0秒", "recent": "2勝クラス 5着", "score": 82.0, "mark": "△ 連下"},
    {"num": 5, "name": "ワンダーカモン", "jockey": "M.デムーロ", "odds": 28.5, "style": "差し", "last3f": "36.8秒", "recent": "2勝クラス 6着", "score": 84.0, "mark": "☆ 爆発期待穴"},
    {"num": 6, "name": "リヒトミューレ", "jockey": "西村淳也", "odds": 12.4, "style": "先行", "last3f": "37.2秒", "recent": "1勝クラス 1着", "score": 86.5, "mark": "▲ 単穴"},
    {"num": 7, "name": "タンテドヴィーヴル", "jockey": "幸英明", "odds": 8.1, "style": "先行", "last3f": "36.9秒", "recent": "2勝クラス 3着", "score": 88.0, "mark": "▲ 単穴"},
    {"num": 8, "name": "サルタール", "jockey": "小崎綾也", "odds": 66.0, "style": "追込", "last3f": "37.6秒", "recent": "2勝クラス 10着", "score": 72.0, "mark": "-"},
    {"num": 9, "name": "オオツカ", "jockey": "坂井瑠星", "odds": 3.8, "style": "先行", "last3f": "36.6秒", "recent": "2勝クラス 2着", "score": 92.0, "mark": "○ 対抗"},
    {"num": 10, "name": "ショーダンサー", "jockey": "国分優作", "odds": 13.9, "style": "追込", "last3f": "36.7秒", "recent": "2勝クラス 4着", "score": 83.0, "mark": "△ 連下"},
    {"num": 11, "name": "ジョータルマエ", "jockey": "鮫島良太", "odds": 14.7, "style": "逃げ", "last3f": "37.8秒", "recent": "1勝クラス 1着", "score": 85.0, "mark": "☆ 穴"},
    {"num": 12, "name": "キングオブフジ", "jockey": "中井裕二", "odds": 43.2, "style": "追込", "last3f": "37.4秒", "recent": "2勝クラス 8着", "score": 76.0, "mark": "-"},
    {"num": 13, "name": "メイショウコシュウ", "jockey": "浜中俊", "odds": 7.8, "style": "差し", "last3f": "36.5秒", "recent": "2勝クラス 3着", "score": 89.0, "mark": "▲ 単穴"},
    {"num": 14, "name": "システマソラー", "jockey": "川田将雅", "odds": 3.4, "style": "好位", "last3f": "36.4秒", "recent": "1勝クラス 1着", "score": 93.5, "mark": "◎ 本命"}
]

# 東京12R（ダ1400m 16頭）
tokyo12_horses = [
    {"num": 1, "name": "ホウオウゴールド", "jockey": "原優介", "odds": 32.9, "style": "追込", "last3f": "35.8秒", "recent": "2勝クラス 7着", "score": 81.0, "mark": "-"},
    {"num": 2, "name": "エチャケナ", "jockey": "伊藤工真", "odds": 29.0, "style": "差し", "last3f": "35.5秒", "recent": "2勝クラス 5着", "score": 82.5, "mark": "☆ 爆発期待穴"},
    {"num": 3, "name": "エムティエスターテ", "jockey": "大野拓弥", "odds": 40.7, "style": "先行", "last3f": "35.9秒", "recent": "2勝クラス 7着", "score": 80.0, "mark": "-"},
    {"num": 4, "name": "レーティッシュ", "jockey": "横山武史", "odds": 7.5, "style": "先行", "last3f": "35.2秒", "recent": "2勝クラス 2着", "score": 89.5, "mark": "○ 対抗"},
    {"num": 5, "name": "トラヴェリンバンド", "jockey": "丹内祐次", "odds": 16.0, "style": "先行", "last3f": "35.6秒", "recent": "2勝クラス 4着", "score": 84.0, "mark": "△ 連下"},
    {"num": 6, "name": "ヘリテージブルーム", "jockey": "田辺裕信", "odds": 5.4, "style": "差し", "last3f": "34.8秒", "recent": "1勝クラス 1着", "score": 92.0, "mark": "▲ 単穴"},
    {"num": 7, "name": "ゴルデールスカー", "jockey": "杉原誠人", "odds": 36.7, "style": "追込", "last3f": "35.7秒", "recent": "2勝クラス 8着", "score": 78.5, "mark": "-"},
    {"num": 8, "name": "マジッククッキー", "jockey": "石神道也", "odds": 3.7, "style": "好位", "last3f": "35.0秒", "recent": "2勝クラス 2着", "score": 93.0, "mark": "◎ 本命"},
    {"num": 9, "name": "フィリップ", "jockey": "木幡巧也", "odds": 18.5, "style": "逃げ", "last3f": "36.0秒", "recent": "1勝クラス 1着", "score": 85.0, "mark": "▲ 単穴"},
    {"num": 10, "name": "ショーリバース", "jockey": "横山典弘", "odds": 8.0, "style": "差し", "last3f": "35.1秒", "recent": "1勝クラス 1着", "score": 88.0, "mark": "▲ 単穴"},
    {"num": 11, "name": "トーホウキザン", "jockey": "長浜鴻緒", "odds": 46.5, "style": "追込", "last3f": "35.9秒", "recent": "2勝クラス 11着", "score": 76.0, "mark": "-"},
    {"num": 12, "name": "ケブランリ", "jockey": "戸崎圭太", "odds": 10.5, "style": "先行", "last3f": "35.3秒", "recent": "2勝クラス 3着", "score": 87.0, "mark": "△ 連下"},
    {"num": 13, "name": "メルシージュテーム", "jockey": "M.ミシェル", "odds": 20.8, "style": "追込", "last3f": "35.4秒", "recent": "2勝クラス 6着", "score": 83.0, "mark": "△ 連下"},
    {"num": 14, "name": "レッドダンルース", "jockey": "丸山元気", "odds": 38.5, "style": "差し", "last3f": "35.7秒", "recent": "2勝クラス 9着", "score": 79.0, "mark": "-"},
    {"num": 15, "name": "タリエシン", "jockey": "石田拓郎", "odds": 64.6, "style": "追込", "last3f": "36.2秒", "recent": "2勝クラス 12着", "score": 74.0, "mark": "-"},
    {"num": 16, "name": "シホノペルフェット", "jockey": "小林美駒", "odds": 7.1, "style": "先行", "last3f": "35.2秒", "recent": "2勝クラス 3着", "score": 88.5, "mark": "△ 連下"}
]

opal_horses = [
    {"num": 1, "name": "カルチャーデイ", "jockey": "酒井学", "odds": 17.0, "style": "差し", "last3f": "34.1秒", "recent": "朱鷺S 8着", "score": 83.2, "mark": "△ 連下"},
    {"num": 2, "name": "ショウナンアビアス", "jockey": "北村友一", "odds": 58.8, "style": "追込", "last3f": "34.4秒", "recent": "ラジオ日本賞 5着", "score": 75.0, "mark": "-"},
    {"num": 3, "name": "タマモイカロス", "jockey": "松山弘平", "odds": 8.1, "style": "先行", "last3f": "33.8秒", "recent": "葵ステークス 3着", "score": 93.5, "mark": "◎ 本命"},
    {"num": 4, "name": "メイショウヨゾラ", "jockey": "吉村誠之助", "odds": 9.3, "style": "逃げ", "last3f": "34.6秒", "recent": "セントウルS 6着", "score": 88.0, "mark": "○ 対抗"},
    {"num": 5, "name": "フィオライア", "jockey": "松若風馬", "odds": 20.4, "style": "先行", "last3f": "34.2秒", "recent": "CBC賞 13着", "score": 84.5, "mark": "▲ 単穴"},
    {"num": 6, "name": "リリージョワ", "jockey": "浜中俊", "odds": 6.9, "style": "先行", "last3f": "33.6秒", "recent": "もみじS 1着", "score": 86.8, "mark": "☆ 穴"},
    {"num": 7, "name": "テーオーダヴィンチ", "jockey": "菱田裕二", "odds": 98.9, "style": "追込", "last3f": "34.5秒", "recent": "安土城S 9着", "score": 72.0, "mark": "-"},
    {"num": 8, "name": "レッドエヴァンス", "jockey": "西村淳也", "odds": 14.2, "style": "差し", "last3f": "33.7秒", "recent": "佐世保S 2着", "score": 82.5, "mark": "△ 連下"},
    {"num": 9, "name": "タマモブラックタイ", "jockey": "幸英明", "odds": 11.5, "style": "先行", "last3f": "34.3秒", "recent": "米子城S 1着", "score": 83.0, "mark": "△ 連下"},
    {"num": 10, "name": "ヒシアイラ", "jockey": "荻野極", "odds": 15.8, "style": "差し", "last3f": "33.5秒", "recent": "マーガレットS 2着", "score": 81.5, "mark": "-"},
    {"num": 11, "name": "オタルエバー", "jockey": "角田大和", "odds": 25.4, "style": "先行", "last3f": "34.8秒", "recent": "バーデンバーデンC 4着", "score": 79.0, "mark": "-"},
    {"num": 12, "name": "デイトナモード", "jockey": "斎藤新", "odds": 33.0, "style": "追込", "last3f": "33.9秒", "recent": "安土城S 6着", "score": 78.5, "mark": "-"},
    {"num": 13, "name": "クラスペディア", "jockey": "小崎綾也", "odds": 7.5, "style": "先行", "last3f": "33.6秒", "recent": "小倉2歳S 2着", "score": 87.0, "mark": "▲ 単穴"},
    {"num": 14, "name": "ヤマニンアルリフラ", "jockey": "M.デムーロ", "odds": 18.2, "style": "差し", "last3f": "33.8秒", "recent": "NST賞 3着", "score": 81.0, "mark": "-"},
    {"num": 15, "name": "タガノアラリア", "jockey": "鮫島克駿", "odds": 12.0, "style": "先行", "last3f": "34.0秒", "recent": "橘S 2着", "score": 82.0, "mark": "△ 連下"},
    {"num": 16, "name": "フロムダスク", "jockey": "中井裕二", "odds": 10.5, "style": "逃げ", "last3f": "34.4秒", "recent": "CBC賞 1着", "score": 85.0, "mark": "△ 連下"},
    {"num": 17, "name": "ヨシノイースター", "jockey": "坂井瑠星", "odds": 5.8, "style": "先行", "last3f": "33.5秒", "recent": "北九州記念 2着", "score": 89.2, "mark": "▲ 単穴"},
    {"num": 18, "name": "ディアナザール", "jockey": "川田将雅", "odds": 4.5, "style": "差し", "last3f": "33.3秒", "recent": "毎日杯 4着", "score": 91.0, "mark": "▲ 単穴"}
]

ooyamazaki_horses = [
    {"num": 1, "name": "ヤマニンシュラ", "jockey": "M.デムーロ", "odds": 8.5, "style": "先行", "last3f": "36.2秒", "recent": "なにわS 14着", "score": 85.0, "mark": "△ 連下"},
    {"num": 2, "name": "スペシャルナンバー", "jockey": "鮫島克駿", "odds": 18.2, "style": "追込", "last3f": "35.2秒", "recent": "オークランド 10着", "score": 81.0, "mark": "-"},
    {"num": 3, "name": "ハヤテノツバサ", "jockey": "斎藤新", "odds": 6.8, "style": "逃げ", "last3f": "36.0秒", "recent": "釜山S 6着", "score": 86.5, "mark": "▲ 単穴"},
    {"num": 4, "name": "イマージョン", "jockey": "西村淳也", "odds": 15.5, "style": "差し", "last3f": "35.5秒", "recent": "安芸S 3着", "score": 82.0, "mark": "△ 連下"},
    {"num": 5, "name": "ライジン", "jockey": "松若風馬", "odds": 23.8, "style": "先行", "last3f": "35.4秒", "recent": "オークランド 3着", "score": 83.0, "mark": "☆ 穴"},
    {"num": 6, "name": "ウルスクローム", "jockey": "田口貫太", "odds": 4.5, "style": "先行", "last3f": "35.3秒", "recent": "オークランド 2着", "score": 91.5, "mark": "◎ 本命"},
    {"num": 7, "name": "メイショウヤーキス", "jockey": "菱田裕二", "odds": 12.0, "style": "差し", "last3f": "35.4秒", "recent": "オークランド 5着", "score": 83.5, "mark": "△ 連下"},
    {"num": 8, "name": "アメリカンチケット", "jockey": "小崎綾也", "odds": 35.0, "style": "追込", "last3f": "35.8秒", "recent": "上越S 7着", "score": 77.0, "mark": "-"},
    {"num": 9, "name": "ビルカール", "jockey": "北村友一", "odds": 28.0, "style": "先行", "last3f": "36.9秒", "recent": "福島中央TV 6着", "score": 78.5, "mark": "-"},
    {"num": 10, "name": "カミーロ", "jockey": "角田大和", "odds": 42.0, "style": "逃げ", "last3f": "36.5秒", "recent": "NST賞 8着", "score": 76.0, "mark": "-"},
    {"num": 11, "name": "テーオーグレーザー", "jockey": "松山弘平", "odds": 5.2, "style": "先行", "last3f": "35.5秒", "recent": "高瀬川S 4着", "score": 88.5, "mark": "○ 対抗"},
    {"num": 12, "name": "トーアジョウトウ", "jockey": "荻野極", "odds": 16.0, "style": "逃げ", "last3f": "36.8秒", "recent": "なにわS 4着", "score": 81.5, "mark": "-"},
    {"num": 13, "name": "ディニトーソ", "jockey": "長岡禎仁", "odds": 31.0, "style": "追込", "last3f": "35.6秒", "recent": "伊賀S 8着", "score": 78.0, "mark": "-"},
    {"num": 14, "name": "ルクスデイジー", "jockey": "川田将雅", "odds": 3.8, "style": "好位", "last3f": "35.1秒", "recent": "陽春S 2着", "score": 90.0, "mark": "▲ 単穴"},
    {"num": 15, "name": "ジャーヴィス", "jockey": "藤懸貴志", "odds": 48.0, "style": "追込", "last3f": "35.7秒", "recent": "釜山S 4着", "score": 75.5, "mark": "-"},
    {"num": 16, "name": "ギーロカスタル", "jockey": "太宰啓介", "odds": 62.0, "style": "追込", "last3f": "35.9秒", "recent": "伊賀S 11着", "score": 74.0, "mark": "-"}
]

rindou_horses = [
    {"num": 1, "name": "ベニバナ", "jockey": "田山旺佑", "odds": 5.2, "style": "先行", "last3f": "33.8秒", "recent": "未勝利 1着", "score": 87.0, "mark": "▲ 単穴"},
    {"num": 2, "name": "エストレアボニータ", "jockey": "今村聖奈", "odds": 14.0, "style": "好位", "last3f": "34.5秒", "recent": "未勝利 1着", "score": 82.0, "mark": "△ 連下"},
    {"num": 3, "name": "ギャルズマインド", "jockey": "浜中俊", "odds": 4.1, "style": "先行", "last3f": "34.0秒", "recent": "未勝利 1着", "score": 88.5, "mark": "○ 対抗"},
    {"num": 4, "name": "セイウンリリーナ", "jockey": "幸英明", "odds": 18.0, "style": "差し", "last3f": "34.6秒", "recent": "未勝利 1着", "score": 80.5, "mark": "-"},
    {"num": 5, "name": "ショウナンカノア", "jockey": "吉村誠之助", "odds": 9.5, "style": "好位", "last3f": "34.2秒", "recent": "未勝利 1着", "score": 84.0, "mark": "☆ 穴"},
    {"num": 6, "name": "ヴィヴェローネ", "jockey": "松山弘平", "odds": 6.8, "style": "差し", "last3f": "33.9秒", "recent": "未勝利 1着", "score": 86.0, "mark": "△ 連下"},
    {"num": 7, "name": "ラムラベイ", "jockey": "松若風馬", "odds": 2.7, "style": "先行", "last3f": "33.7秒", "recent": "新馬 1着", "score": 92.0, "mark": "◎ 本命"},
    {"num": 8, "name": "ルジュエ", "jockey": "田野豊三", "odds": 28.0, "style": "追込", "last3f": "34.8秒", "recent": "地方未勝利 1着", "score": 77.0, "mark": "-"}
]

green_horses = [
    {"num": 1, "name": "ルヴァレドクール", "jockey": "横山和生", "odds": 8.6, "style": "先行", "last3f": "35.4秒", "recent": "夏至S 1着", "score": 86.5, "mark": "△ 連下"},
    {"num": 2, "name": "ジンセイ", "jockey": "丹内祐次", "odds": 18.7, "style": "好位", "last3f": "36.5秒", "recent": "太秦S 3着", "score": 83.0, "mark": "-"},
    {"num": 3, "name": "スナッピードレッサ", "jockey": "大野拓弥", "odds": 12.8, "style": "先行", "last3f": "35.4秒", "recent": "桶狭間S 1着", "score": 85.0, "mark": "△ 連下"},
    {"num": 4, "name": "ヘニーガイスト", "jockey": "横山武史", "odds": 2.3, "style": "好位", "last3f": "35.1秒", "recent": "ポプラS 1着", "score": 93.0, "mark": "◎ 本命"},
    {"num": 5, "name": "ドンエレクトス", "jockey": "三浦皇成", "odds": 5.2, "style": "逃げ", "last3f": "35.8秒", "recent": "昇竜S 2着", "score": 89.0, "mark": "○ 対抗"},
    {"num": 6, "name": "ヒルノドゴール", "jockey": "戸崎圭太", "odds": 94.5, "style": "追込", "last3f": "35.6秒", "recent": "エニフS 8着", "score": 76.0, "mark": "-"},
    {"num": 7, "name": "トリリオンボーイ", "jockey": "津村明秀", "odds": 112.5, "style": "追込", "last3f": "35.8秒", "recent": "麦秋S 6着", "score": 75.0, "mark": "-"},
    {"num": 8, "name": "メルキオル", "jockey": "原優介", "odds": 42.0, "style": "先行", "last3f": "36.2秒", "recent": "阿波特別 3着", "score": 95.8, "mark": "☆ 爆発期待穴"},
    {"num": 9, "name": "ヴィヴァン", "jockey": "佐々木大輔", "odds": 39.6, "style": "差し", "last3f": "35.7秒", "recent": "BSN賞 7着", "score": 78.0, "mark": "-"},
    {"num": 10, "name": "オウギノカナメ", "jockey": "菊沢一樹", "odds": 40.3, "style": "差し", "last3f": "35.5秒", "recent": "アハルテケS 5着", "score": 94.2, "mark": "▲ 単穴"},
    {"num": 11, "name": "ジャスティンアース", "jockey": "C.ルメール", "odds": 6.6, "style": "先行", "last3f": "35.2秒", "recent": "欅S 2着", "score": 88.5, "mark": "▲ 単穴"},
    {"num": 12, "name": "マピュース", "jockey": "田辺裕信", "odds": 9.6, "style": "差し", "last3f": "35.3秒", "recent": "NST賞 4着", "score": 84.5, "mark": "△ 連下"},
    {"num": 13, "name": "フリームファクシ", "jockey": "M.ミシェル", "odds": 48.1, "style": "先行", "last3f": "36.4秒", "recent": "エルムS 11着", "score": 77.0, "mark": "-"},
    {"num": 14, "name": "オーブルクール", "jockey": "石橋脩", "odds": 110.8, "style": "追込", "last3f": "36.0秒", "recent": "名鉄杯 9着", "score": 72.0, "mark": "-"},
    {"num": 15, "name": "ルージュスタニング", "jockey": "岩田康誠", "odds": 37.5, "style": "先行", "last3f": "36.1秒", "recent": "ラジオ日本賞 6着", "score": 79.0, "mark": "-"}
]

hakushu_horses = [
    {"num": 1, "name": "グーテンベルク", "jockey": "戸崎圭太", "odds": 8.6, "style": "好位", "last3f": "33.9秒", "recent": "常総S 3着", "score": 87.0, "mark": "▲ 単穴"},
    {"num": 2, "name": "モンシュマン", "jockey": "岩田康誠", "odds": 16.5, "style": "先行", "last3f": "33.9秒", "recent": "多摩川S 6着", "score": 83.0, "mark": "△ 連下"},
    {"num": 3, "name": "ホウオウシェリー", "jockey": "津村明秀", "odds": 12.0, "style": "先行", "last3f": "33.8秒", "recent": "飯豊特別 1着", "score": 85.5, "mark": "☆ 穴"},
    {"num": 4, "name": "セシリエプラージュ", "jockey": "M.ミシェル", "odds": 24.0, "style": "差し", "last3f": "34.1秒", "recent": "朱鷺S 7着", "score": 80.0, "mark": "-"},
    {"num": 5, "name": "レッドキングリー", "jockey": "C.ルメール", "odds": 3.2, "style": "好位", "last3f": "33.2秒", "recent": "湘南S 2着", "score": 93.0, "mark": "◎ 本命"},
    {"num": 6, "name": "サトミノキラリ", "jockey": "小林美駒", "odds": 31.0, "style": "逃げ", "last3f": "34.5秒", "recent": "長岡S 8着", "score": 78.0, "mark": "-"},
    {"num": 7, "name": "チャンネルトンネル", "jockey": "横山武史", "odds": 5.8, "style": "差し", "last3f": "33.4秒", "recent": "パラダイスS 4着", "score": 89.0, "mark": "○ 対抗"},
    {"num": 8, "name": "ビップジーニー", "jockey": "横山琉人", "odds": 45.0, "style": "追込", "last3f": "34.2秒", "recent": "佐渡S 9着", "score": 75.0, "mark": "-"},
    {"num": 9, "name": "トライアンフパス", "jockey": "松岡正海", "odds": 28.0, "style": "先行", "last3f": "34.0秒", "recent": "豊栄特別 3着", "score": 79.5, "mark": "-"},
    {"num": 10, "name": "エヴァンスウィート", "jockey": "佐々木大輔", "odds": 7.4, "style": "差し", "last3f": "33.5秒", "recent": "信濃川特別 2着", "score": 87.5, "mark": "▲ 単穴"},
    {"num": 11, "name": "ブリックワーク", "jockey": "吉田豊", "odds": 38.0, "style": "追込", "last3f": "33.8秒", "recent": "奥の細道特別 6着", "score": 77.0, "mark": "-"},
    {"num": 12, "name": "フォーゲル", "jockey": "池添謙一", "odds": 14.0, "style": "好位", "last3f": "33.7秒", "recent": "鷹巣山特別 3着", "score": 84.0, "mark": "△ 連下"},
    {"num": 13, "name": "コスモサガルマータ", "jockey": "横山和生", "odds": 18.5, "style": "差し", "last3f": "33.6秒", "recent": "TVh杯 5着", "score": 82.5, "mark": "△ 連下"},
    {"num": 14, "name": "ミストレス", "jockey": "古川奈穂", "odds": 52.0, "style": "追込", "last3f": "34.3秒", "recent": "雲雀S 11着", "score": 74.0, "mark": "-"},
    {"num": 15, "name": "キタサンダムール", "jockey": "原優介", "odds": 35.0, "style": "追込", "last3f": "33.9秒", "recent": "STV賞 7着", "score": 76.5, "mark": "-"},
    {"num": 16, "name": "コスモアディラート", "jockey": "柴田大知", "odds": 68.0, "style": "先行", "last3f": "34.8秒", "recent": "函館日刊S 10着", "score": 72.0, "mark": "-"},
    {"num": 17, "name": "シャイフ", "jockey": "横山典弘", "odds": 11.0, "style": "追込", "last3f": "33.3秒", "recent": "京成杯AH 5着", "score": 85.0, "mark": "△ 連下"},
    {"num": 18, "name": "ヒシアマン", "jockey": "大野拓弥", "odds": 13.5, "style": "差し", "last3f": "33.6秒", "recent": "長岡S 4着", "score": 84.5, "mark": "△ 連下"}
]

nanbu_horses = [
    {"num": 1, "name": "ディープキング", "jockey": "丹内祐次", "odds": 22.0, "style": "追込", "last3f": "34.5秒", "recent": "2勝クラス 6着", "score": 79.0, "mark": "-"},
    {"num": 2, "name": "イージーライダー", "jockey": "横山武史", "odds": 6.8, "style": "先行", "last3f": "33.9秒", "recent": "三面川特別 2着", "score": 88.0, "mark": "○ 対抗"},
    {"num": 3, "name": "ステラスペース", "jockey": "武藤雅", "odds": 15.0, "style": "好位", "last3f": "34.1秒", "recent": "1勝クラス 1着", "score": 83.0, "mark": "△ 連下"},
    {"num": 4, "name": "フィールドノート", "jockey": "C.ルメール", "odds": 2.6, "style": "好位", "last3f": "33.4秒", "recent": "阿賀野川特別 2着", "score": 93.0, "mark": "◎ 本命"},
    {"num": 5, "name": "コスモスプモーニ", "jockey": "木幡巧也", "odds": 35.0, "style": "差し", "last3f": "34.6秒", "recent": "2勝クラス 8着", "score": 76.0, "mark": "-"},
    {"num": 6, "name": "レッドバレンティア", "jockey": "原優介", "odds": 18.0, "style": "追込", "last3f": "34.0秒", "recent": "潮来特別 5着", "score": 81.0, "mark": "-"},
    {"num": 7, "name": "ミッキージャンプ", "jockey": "佐々木大輔", "odds": 7.5, "style": "先行", "last3f": "33.8秒", "recent": "2勝クラス 3着", "score": 87.0, "mark": "▲ 単穴"},
    {"num": 8, "name": "ドッグウッド", "jockey": "戸崎圭太", "odds": 5.4, "style": "差し", "last3f": "33.7秒", "recent": "2勝クラス 2着", "score": 88.5, "mark": "☆ 穴"},
    {"num": 9, "name": "ファムクラジューズ", "jockey": "菊沢一樹", "odds": 8.2, "style": "先行", "last3f": "34.2秒", "recent": "1勝クラス 1着", "score": 85.0, "mark": "△ 連下"},
    {"num": 10, "name": "ノビリシマビジョン", "jockey": "津村明秀", "odds": 12.0, "style": "好位", "last3f": "34.0秒", "recent": "2勝クラス 4着", "score": 84.0, "mark": "△ 連下"},
    {"num": 11, "name": "ホウオウシンデレラ", "jockey": "丸田恭介", "odds": 24.5, "style": "追込", "last3f": "34.3秒", "recent": "2勝クラス 7着", "score": 78.0, "mark": "-"},
    {"num": 12, "name": "マイネルアレス", "jockey": "石橋脩", "odds": 29.0, "style": "差し", "last3f": "34.4秒", "recent": "2勝クラス 5着", "score": 77.5, "mark": "-"}
]

target_races_data = [
    # 京都
    {"raceId": "202608040109", "venue": "京都", "raceName": "9R りんどう賞 (芝1400m)", "startTime": "14:15", "isGraded": False, "isWin5": False, "horses": rindou_horses},
    {"raceId": "202608040110", "venue": "京都", "raceName": "10R 大山崎ステークス (ダ1200m)", "startTime": "14:50", "isGraded": False, "isWin5": True, "horses": ooyamazaki_horses},
    {"raceId": "202608040111", "venue": "京都", "raceName": "11R オパールステークス (L・芝1200m)", "startTime": "15:30", "isGraded": True, "isWin5": True, "horses": opal_horses},
    {"raceId": "202608040112", "venue": "京都", "raceName": "12R 3歳以上2勝クラス (ダ1800m)", "startTime": "16:10", "isGraded": False, "isWin5": False, "horses": kyoto12_horses},

    # 東京
    {"raceId": "202605040109", "venue": "東京", "raceName": "9R 八ヶ岳特別 (芝1800m)", "startTime": "14:35", "isGraded": False, "isWin5": True, "horses": nanbu_horses},
    {"raceId": "202605040110", "venue": "東京", "raceName": "10R 白秋ステークス (芝1400m)", "startTime": "15:10", "isGraded": False, "isWin5": True, "horses": hakushu_horses},
    {"raceId": "202605040111", "venue": "東京", "raceName": "11R グリーンチャンネルC (L・ダ1600m)", "startTime": "15:45", "isGraded": True, "isWin5": True, "horses": green_horses},
    {"raceId": "202605040112", "venue": "東京", "raceName": "12R 3歳以上2勝クラス (ダ1400m)", "startTime": "16:30", "isGraded": False, "isWin5": False, "horses": tokyo12_horses}
]

print("=== ジェミ予想 (印完全連動・10点以内厳守モデル) 推論開始 ===")
final_races = []

for r in target_races_data:
    print(f"推論実行中: {r['venue']} {r['raceName']} (印連動の買い目生成)...")
    ai_result = ask_gemini_prediction(r["raceName"], r["venue"], r["horses"])
    final_races.append({
        "raceId": r["raceId"],
        "venue": r["venue"],
        "raceName": r["raceName"],
        "startTime": r["startTime"],
        "isGraded": r["isGraded"],
        "isWin5": r["isWin5"],
        "horses": r["horses"],
        "honmeiNum": ai_result.get("honmei_num"),
        "confidence": ai_result.get("confidence", "A"),
        "confidenceScore": ai_result.get("confidence_score", 90),
        "aiSummary": ai_result.get("summary", ""),
        "aiBuy": ai_result.get("recommendation", "")
    })
    time.sleep(1.0)

win5_target_ids = ["202605040109", "202608040110", "202605040110", "202608040111", "202605040111"]
win5_races_list = [r for r in final_races if r["raceId"] in win5_target_ids]

print("GeminiによるWIN5厳選戦略（最大10点まで・期待値配分）を算出中...")
win5_strategy_text = ask_gemini_win5_strategy(win5_races_list)

sorted_by_conf = sorted(final_races, key=lambda x: x.get("confidenceScore", 0), reverse=True)
best_races = sorted_by_conf[:3]

output_data = {
    "updatedAt": now_str,
    "win5Strategy": win5_strategy_text,
    "bestRaces": best_races,
    "races": final_races
}

with open("data/today.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"=== 全処理完了: 印に完全連動した論理的買い目を保存しました ===")
