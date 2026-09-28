import os
import json
from datetime import datetime

os.makedirs("data", exist_ok=True)
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

full_data = {
    "updatedAt": now_str,
    "races": [
        {
            "venue": "中山",
            "raceName": "11R スプリンターズS (G1)",
            "startTime": "15:45",
            "horses": [
                {"num": 1, "name": "オオバンブルマイ", "jockey": "武豊", "odds": 17.1, "score": 82.5, "mark": "▲ 単穴"},
                {"num": 2, "name": "トウシンマカオ", "jockey": "菅原明良", "odds": 9.6, "score": 85.0, "mark": "○ 対抗"},
                {"num": 3, "name": "ウインマーベル", "jockey": "松山弘平", "odds": 14.2, "score": 79.8, "mark": "-"},
                {"num": 4, "name": "エイシンスポッター", "jockey": "A.シュタルケ", "odds": 45.0, "score": 74.2, "mark": "-"},
                {"num": 5, "name": "ナムラクレア", "jockey": "横山武史", "odds": 8.2, "score": 84.1, "mark": "☆ 穴"},
                {"num": 6, "name": "ママコチャ", "jockey": "川田将雅", "odds": 5.2, "score": 81.3, "mark": "-"},
                {"num": 7, "name": "マッドクール", "jockey": "坂井瑠星", "odds": 11.5, "score": 80.1, "mark": "-"},
                {"num": 8, "name": "モズメイメイ", "jockey": "国分恭介", "odds": 38.4, "score": 75.0, "mark": "-"},
                {"num": 9, "name": "ムゲン", "jockey": "K.ティータン", "odds": 22.0, "score": 77.4, "mark": "-"},
                {"num": 10, "name": "ピューロマジック", "jockey": "横山和生", "odds": 19.8, "score": 78.5, "mark": "-"},
                {"num": 11, "name": "ダノンスマッシュ", "jockey": "三浦皇成", "odds": 52.3, "score": 72.0, "mark": "-"},
                {"num": 12, "name": "サトノレーヴ", "jockey": "D.レーン", "odds": 3.0, "score": 80.9, "mark": "△ 連下"},
                {"num": 13, "name": "ルガル", "jockey": "西村淳也", "odds": 28.5, "score": 88.4, "mark": "◎ 本命"},
                {"num": 14, "name": "ビクターザウィナー", "jockey": "C.ホー", "odds": 15.6, "score": 79.0, "mark": "-"},
                {"num": 15, "name": "ヴェントヴォーチェ", "jockey": "C.ルメール", "odds": 33.1, "score": 76.5, "mark": "-"},
                {"num": 16, "name": "ウイングレイテスト", "jockey": "松岡正海", "odds": 64.0, "score": 71.2, "mark": "-"}
            ]
        },
        {
            "venue": "阪神",
            "raceName": "11R 神戸新聞杯 (G2)",
            "startTime": "15:35",
            "horses": [
                {"num": 1, "name": "ジューンテイク", "jockey": "藤岡佑介", "odds": 12.4, "score": 81.2, "mark": "☆ 穴"},
                {"num": 2, "name": "バッデレイト", "jockey": "岩田望来", "odds": 7.5, "score": 83.5, "mark": "○ 対抗"},
                {"num": 3, "name": "ヴィレム", "jockey": "団野大成", "odds": 24.1, "score": 75.3, "mark": "-"},
                {"num": 4, "name": "ミスタージーティー", "jockey": "坂井瑠星", "odds": 18.0, "score": 77.0, "mark": "-"},
                {"num": 5, "name": "オールセインツ", "jockey": "岩田康誠", "odds": 9.8, "score": 79.5, "mark": "-"},
                {"num": 6, "name": "メリオーレム", "jockey": "川田将雅", "odds": 2.8, "score": 82.0, "mark": "▲ 単穴"},
                {"num": 7, "name": "ヴィヒタ", "jockey": "幸英明", "odds": 48.0, "score": 73.1, "mark": "-"},
                {"num": 8, "name": "ヤマニンステラータ", "jockey": "池添謙一", "odds": 35.2, "score": 74.5, "mark": "-"},
                {"num": 9, "name": "トラストボス", "jockey": "角田大和", "odds": 82.0, "score": 69.8, "mark": "-"},
                {"num": 10, "name": "インテグレティ", "jockey": "松若風馬", "odds": 55.4, "score": 71.0, "mark": "-"},
                {"num": 11, "name": "ショウナンラプンタ", "jockey": "鮫島克駿", "odds": 6.2, "score": 80.5, "mark": "△ 連下"},
                {"num": 12, "name": "メイショウタバル", "jockey": "浜中俊", "odds": 5.1, "score": 87.0, "mark": "◎ 本命"},
                {"num": 13, "name": "ゴージョバウンド", "jockey": "和田竜二", "odds": 66.5, "score": 70.2, "mark": "-"},
                {"num": 14, "name": "サブマリーナ", "jockey": "武豊", "odds": 16.3, "score": 78.0, "mark": "-"},
                {"num": 15, "name": "キープカルム", "jockey": "横山典弘", "odds": 29.0, "score": 76.1, "mark": "-"}
            ]
        }
    ]
}

with open("data/today.json", "w", encoding="utf-8") as f:
    json.dump(full_data, f, ensure_ascii=False, indent=2)

print("Saved full race data successfully.")
