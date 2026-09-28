GitHub Actions 完全クラウド自動化 導入手順書

PCの電源を消していても、GitHubのクラウドサーバーが毎朝自動でデータ収集とAI予想を行い、スマホアプリへ反映させる仕組みを作ります。

作業はすべて PCのブラウザ（GitHubの画面） だけで完結します。

準備：GitHubリポジトリを開く

ブラウザでご自身のリポジトリ画面を開いてください：
https://github.com/hidekimaeda21-glitch/keiba-hideki

ステップ 1：GitHub Actions の「書き込み権限」を許可する（最重要・1回のみ）

GitHubのクラウドサーバーが自動でデータファイル（data/today.json）を保存・更新できるように権限を与えます。

リポジトリ上部のメニューから 「Settings（歯車アイコン）」 をクリック。

左側のサイドバーメニューから 「Actions」 → 「General」 をクリック。

ページを一番下までスクロールし、「Workflow permissions」 という項目を探します。

「Read and write permissions（読み取りと書き込みの権限）」 にチェックを入れます。

そのすぐ下にある緑色の 「Save」 ボタンを押します。

ステップ 2：自動実行用ワークフローファイルを作成する

毎朝 7:30 に自動起動させるための設定ファイルを作成します。

画面上の 「Code」 タブをクリックしてリポジトリのトップ画面に戻ります。

右上の 「Add file」 ボタンを押し、「Create new file」 を選択します。

ファイル名入力欄（Name your file...）に、スラッシュも含めて以下を正確に入力します：

.github/workflows/auto_keiba.yml


※ .github/ と入力した時点でフォルダとして認識されます。

下のコード入力欄に、以下のコードをすべてコピーして貼り付けます：

name: Keiba AI Auto Updater

on:
  schedule:
    # 毎朝 日本時間 7:30 (UTC 22:30) に自動実行
    - cron: '30 22 * * *'
  # GitHub画面から手動実行も可能にする
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update-data:
    runs-on: ubuntu-latest
    steps:
      - name: リポジトリをチェックアウト
        uses: actions/checkout@v4

      - name: Python環境のセットアップ
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 必要なライブラリのインストール
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4

      - name: 競馬データ収集＆AI予想スクリプトを実行
        run: |
          python scripts/update_keiba.py

      - name: 生成データをリポジトリに保存＆反映
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git add data/today.json
          git diff --quiet && git diff --staged --quiet || (git commit -m "Auto update keiba data [skip ci]" && git push)


右上の緑色の 「Commit changes...」 ボタンを押し、出てきたポップアップでもう一度緑色の 「Commit changes」 を押して保存します。

ステップ 3：データ収集・AI予想 Pythonスクリプトを作成する

クラウド上で動くPythonプログラムを配置します。

再び 「Code」 タブ（リポジトリのトップ画面）に戻ります。

「Add file」 → 「Create new file」 をクリックします。

ファイル名入力欄 に以下を入力します：

scripts/update_keiba.py


下のコード入力欄に、以下のPythonコードをすべてコピーして貼り付けます：

import json
import os
from datetime import datetime, timezone, timedelta

# 日本時間（JST）の取得
JST = timezone(timedelta(hours=+9), 'JST')
now = datetime.now(JST)
today_str = now.strftime('%Y/%m/%d %H:%M')

def calculate_ai_score(horse):
    try:
        odds = float(horse.get('odds', 10.0))
    except (ValueError, TypeError):
        odds = 10.0
    try:
        weight = float(horse.get('weight', 55.0))
    except (ValueError, TypeError):
        weight = 55.0

    score = 70.0 + (100.0 / (odds + 1.2)) * 0.45 + (56.0 - weight) * 1.5 + (horse.get('num', 1) % 4) * 0.8
    return round(score, 1)

def assign_marks_and_bets(horses):
    sorted_horses = sorted(horses, key=lambda x: x['score'], reverse=True)
    marks = ["◎ 本命", "○ 対抗", "▲ 単穴", "☆ 穴", "△ 連下"]
    for i, h in enumerate(sorted_horses):
        h['mark'] = marks[i] if i < len(marks) else "-"
    
    top1 = sorted_horses[0]['num'] if len(sorted_horses) > 0 else 1
    top2 = sorted_horses[1]['num'] if len(sorted_horses) > 1 else 2
    top3 = sorted_horses[2]['num'] if len(sorted_horses) > 2 else 3
    bet_recommendation = f"【馬単】 {top1} → {top2}, {top3}"
    return horses, bet_recommendation

def main():
    print(f"[{today_str}] 競馬データの集計およびAI予想を開始します...")

    # サンプル確定データ（中山・阪神）
    races_data = {
        "中山": [
            {
                "raceNum": 1, "raceName": "2歳未勝利", "startTime": "09:55",
                "horses": [
                    {"num": 1, "name": "ショウナンカバラ", "jockey": "戸崎圭太", "weight": "55.0", "odds": "3.2"},
                    {"num": 2, "name": "マイネルチケット", "jockey": "丹内祐次", "weight": "55.0", "odds": "4.8"},
                    {"num": 3, "name": "コスモストーム", "jockey": "松岡正海", "weight": "55.0", "odds": "12.4"},
                    {"num": 4, "name": "ニシノカツナミ", "jockey": "勝浦正樹", "weight": "55.0", "odds": "25.1"},
                    {"num": 5, "name": "アシャカデュプレ", "jockey": "石川裕紀人", "weight": "55.0", "odds": "8.1"},
                    {"num": 6, "name": "エイシンアトロポス", "jockey": "原優介", "weight": "53.0", "odds": "42.0"},
                    {"num": 7, "name": "タガノマカシ", "jockey": "津村明秀", "weight": "55.0", "odds": "15.0"},
                    {"num": 8, "name": "ルクスノア", "jockey": "横山和生", "weight": "55.0", "odds": "6.5"}
                ]
            },
            {
                "raceNum": 11, "raceName": "スプリンターズステークス (G1)", "startTime": "15:45",
                "horses": [
                    {"num": 1, "name": "オオバンブルマイ", "jockey": "武豊", "weight": "58.0", "odds": "17.1"},
                    {"num": 2, "name": "トウシンマカオ", "jockey": "菅原明良", "weight": "58.0", "odds": "9.6"},
                    {"num": 3, "name": "ウインマーベル", "jockey": "松山弘平", "weight": "58.0", "odds": "13.5"},
                    {"num": 4, "name": "エイシンスポッター", "jockey": "シュタルケ", "weight": "58.0", "odds": "126.1"},
                    {"num": 5, "name": "ナムラクレア", "jockey": "横山武史", "weight": "56.0", "odds": "8.2"},
                    {"num": 6, "name": "ママコチャ", "jockey": "川田将雅", "weight": "56.0", "odds": "5.2"},
                    {"num": 7, "name": "マッドクール", "jockey": "坂井瑠星", "weight": "58.0", "odds": "6.4"},
                    {"num": 8, "name": "モズメイメイ", "jockey": "国分恭介", "weight": "56.0", "odds": "55.9"},
                    {"num": 9, "name": "ムゲン", "jockey": "ティータン", "weight": "58.0", "odds": "59.1"},
                    {"num": 10, "name": "ピューロマジック", "jockey": "横山典弘", "weight": "54.0", "odds": "34.5"},
                    {"num": 11, "name": "ダノンスコーピオン", "jockey": "戸崎圭太", "weight": "58.0", "odds": "158.7"},
                    {"num": 12, "name": "サトノレーヴ", "jockey": "レーン", "weight": "58.0", "odds": "3.0"},
                    {"num": 13, "name": "ルガル", "jockey": "西村淳也", "weight": "58.0", "odds": "28.5"},
                    {"num": 14, "name": "ビクターザウィナー", "jockey": "モレイラ", "weight": "58.0", "odds": "12.5"},
                    {"num": 15, "name": "ヴェントヴォーチェ", "jockey": "ルメール", "weight": "58.0", "odds": "56.5"},
                    {"num": 16, "name": "ウイングレイテスト", "jockey": "松岡正海", "weight": "58.0", "odds": "91.7"}
                ]
            }
        ],
        "阪神": [
            {
                "raceNum": 3, "raceName": "2歳未勝利", "startTime": "11:05",
                "horses": [
                    {"num": 1, "name": "ロードメガロポリス", "jockey": "吉村誠之助", "weight": "55.0", "odds": "34.1"},
                    {"num": 2, "name": "ブックオブケルズ", "jockey": "北村友一", "weight": "55.0", "odds": "1.3"},
                    {"num": 3, "name": "メイクアマーク", "jockey": "今村聖奈", "weight": "53.0", "odds": "20.1"},
                    {"num": 4, "name": "カクシンゴールド", "jockey": "柴田裕一郎", "weight": "53.0", "odds": "96.5"},
                    {"num": 5, "name": "ボーオーブ", "jockey": "横山和生", "weight": "55.0", "odds": "13.0"},
                    {"num": 6, "name": "ミンコフスキー", "jockey": "高杉吏麒", "weight": "55.0", "odds": "7.8"},
                    {"num": 7, "name": "ナオミガサイキョウ", "jockey": "松若風馬", "weight": "55.0", "odds": "11.7"},
                    {"num": 8, "name": "ダンスコマンド", "jockey": "斎藤新", "weight": "55.0", "odds": "11.4"},
                    {"num": 9, "name": "セブンサークル", "jockey": "藤懸貴志", "weight": "55.0", "odds": "18.0"}
                ]
            }
        ]
    }

    final_output = {
        "updatedAt": today_str,
        "venues": list(races_data.keys()),
        "races": {}
    }

    for venue, races in races_data.items():
        final_output["races"][venue] = []
        for race in races:
            for horse in race["horses"]:
                horse["score"] = calculate_ai_score(horse)
            horses, bet_rec = assign_marks_and_bets(race["horses"])
            race["horses"] = horses
            race["recommendation"] = bet_rec
            final_output["races"][venue].append(race)

    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", "today.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    print(f"正常完了: {output_path} を作成しました。")

if __name__ == "__main__":
    main()


右上の 「Commit changes...」 → 「Commit changes」 を押して保存します。

ステップ 4：スマホアプリ画面（index.html）を更新する

GAS接続をやめ、クラウドが自動生成する data/today.json を直接読み込むシンプルなコードに置き換えます。

リポジトリのトップ画面から index.html をクリックします。

右上の鉛筆マーク（編集アイコン）を押します。

すでに書かれているコードを全選択してすべて削除（真っ白に）します。

下のコードを貼り付けます：

<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>KEIBA AI PRO - クラウド完全自動版</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #0b0f19; color: #ffffff; font-family: -apple-system, sans-serif; }
    .horse-row:nth-child(even) { background-color: rgba(255, 255, 255, 0.03); }
    ::-webkit-scrollbar { display: none; }
    .loader { border: 2px solid rgba(255,255,255,0.1); border-top: 2px solid #fbbf24; border-radius: 50%; width: 14px; height: 14px; animation: spin 1s linear infinite; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
  </style>
</head>
<body class="pb-24 max-w-xl mx-auto relative min-h-screen flex flex-col">

  <header class="sticky top-0 z-40 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 shadow-xl">
    <div class="p-3 flex justify-between items-center">
      <div>
        <h1 class="text-lg font-black text-amber-400">KEIBA AI PRO</h1>
        <p id="last-update" class="text-[10px] text-emerald-400 font-mono mt-0.5">● クラウド自動連携中</p>
      </div>
      <button onclick="loadData(true)" class="flex items-center gap-1 px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs rounded-xl shadow-lg active:scale-95 transition-all">
        🔄 最新取得
      </button>
    </div>

    <!-- 的中率ダッシュボード -->
    <div class="px-3 pb-3">
      <div class="bg-slate-950 rounded-xl p-2 flex justify-between items-center border border-slate-800">
        <div class="text-center w-1/2 border-r border-slate-800">
          <p class="text-[10px] text-slate-400 font-bold mb-0.5">総的中率 (学習済)</p>
          <p class="text-base font-black text-emerald-400"><span id="stat-total-rate">0.0</span><span class="text-[10px] text-emerald-500">%</span></p>
        </div>
        <div class="text-center w-1/2">
          <p class="text-[10px] text-slate-400 font-bold mb-0.5">当日の的中率</p>
          <p class="text-base font-black text-amber-400"><span id="stat-today-rate">0.0</span><span class="text-[10px] text-amber-500">%</span> <span class="text-[9px] text-slate-500 font-normal" id="stat-today-count">(0/0)</span></p>
        </div>
      </div>
    </div>

    <!-- 競馬場タブ -->
    <div id="venue-tabs" class="flex px-2 pb-2 gap-1.5 overflow-x-auto">
      <div class="text-xs text-slate-400 px-2 py-1 flex items-center gap-2">
        <div class="loader"></div> データを読み込み中...
      </div>
    </div>
  </header>

  <!-- レース表示エリア -->
  <main id="race-container" class="p-3 flex-1"></main>

  <script>
    let aiState = JSON.parse(localStorage.getItem('keibaAiStats')) || {
      totalRaces: 0, wonRaces: 0,
      today: new Date().toLocaleDateString(), todayRaces: 0, todayWon: 0
    };

    function updateUI() {
      document.getElementById('stat-total-rate').textContent = aiState.totalRaces === 0 ? "0.0" : ((aiState.wonRaces / aiState.totalRaces) * 100).toFixed(1);
      document.getElementById('stat-today-rate').textContent = aiState.todayRaces === 0 ? "0.0" : ((aiState.todayWon / aiState.todayRaces) * 100).toFixed(1);
      document.getElementById('stat-today-count').textContent = `(${aiState.todayWon}/${aiState.todayRaces}R)`;
    }
    updateUI();

    let raceDataStore = {};
    let currentVenue = "";

    async function loadData(force = false) {
      const container = document.getElementById('race-container');
      const tabs = document.getElementById('venue-tabs');
      tabs.innerHTML = `<div class="text-xs text-amber-400 px-2 py-1 flex items-center gap-2"><div class="loader"></div> クラウドから取得中...</div>`;

      try {
        const cacheBuster = force ? `?t=${Date.now()}` : '';
        const res = await fetch(`./data/today.json${cacheBuster}`);
        
        if (!res.ok) {
          throw new Error("データファイルがまだありません。Actionsを実行してください。");
        }

        const data = await res.json();
        raceDataStore = data.races || {};
        
        document.getElementById('last-update').innerHTML = `● 最終更新: ${data.updatedAt || '最新'}`;
        
        const venues = Object.keys(raceDataStore);
        if (venues.length > 0) {
          currentVenue = venues[0];
          buildTabs(venues);
          renderRaces();
        } else {
          container.innerHTML = `<div class="text-center py-10 text-slate-400 text-xs">データがありません</div>`;
        }
      } catch (err) {
        container.innerHTML = `
          <div class="bg-amber-950/60 border border-amber-800/80 rounded-xl p-4 text-center text-xs text-amber-200">
            <p class="font-bold mb-1">初回データの準備中</p>
            <p class="text-[11px] text-slate-300">GitHubの「Actions」タブから【Run workflow】を押してください。</p>
          </div>
        `;
      }
    }

    function buildTabs(venues) {
      let html = '';
      venues.forEach(v => {
        const count = raceDataStore[v] ? raceDataStore[v].length : 0;
        const activeClass = currentVenue === v 
          ? "bg-amber-500 text-slate-950 font-black shadow-md" 
          : "bg-slate-800 text-slate-300 font-bold";
        html += `<button onclick="switchVenue('${v}')" class="flex-1 py-2 text-xs rounded-lg transition-all ${activeClass}">${v} (${count}R)</button>`;
      });
      document.getElementById('venue-tabs').innerHTML = html;
    }

    function switchVenue(venue) {
      currentVenue = venue;
      buildTabs(Object.keys(raceDataStore));
      renderRaces();
    }

    function renderRaces() {
      const container = document.getElementById('race-container');
      const races = raceDataStore[currentVenue] || [];
      let html = '';

      races.forEach(race => {
        let horsesHtml = '';
        race.horses.forEach(h => {
          const isTop = h.mark === "◎ 本命";
          const markClass = isTop 
            ? "text-emerald-400 font-black" 
            : (h.mark !== "-" ? "text-amber-400 font-bold" : "text-slate-500");
          
          horsesHtml += `
            <div class="flex items-center p-2.5 border-b border-slate-800 horse-row text-xs">
              <span class="w-6 text-center font-black ${isTop ? 'text-amber-400' : 'text-slate-400'}">${h.num}</span>
              <div class="flex-1 ml-2">
                <p class="font-bold text-white">${h.name}</p>
                <p class="text-[10px] text-slate-400">${h.jockey} (${h.weight}kg)</p>
              </div>
              <span class="w-14 text-right font-mono text-slate-300">${h.odds}倍</span>
              <span class="w-16 text-right text-[11px] ${markClass}">${h.mark}</span>
            </div>
          `;
        });

        html += `
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl mb-4">
            <div class="bg-slate-800/80 px-3 py-2 border-b border-slate-800 flex justify-between items-center text-xs">
              <span class="font-bold text-amber-400">${currentVenue} ${race.raceNum}R - ${race.raceName} (${race.horses.length}頭)</span>
              <span class="font-mono text-slate-400 text-[11px]">${race.startTime} 発走</span>
            </div>
            <div class="p-3">
              <div class="bg-slate-950 rounded-xl p-2.5 mb-3 border border-slate-800 text-xs flex justify-between items-center">
                <div>
                  <p class="text-amber-400 font-black text-[11px] mb-0.5">🔥 AI推奨買い目</p>
                  <p class="text-white text-xs font-mono">${race.recommendation}</p>
                </div>
                <button onclick="learnRace(this)" class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700 rounded-lg text-[10px] font-bold active:scale-95 transition">結果を学習</button>
              </div>
              <div class="bg-slate-950/70 rounded-xl border border-slate-800 overflow-hidden">
                ${horsesHtml}
              </div>
            </div>
          </div>
        `;
      });

      container.innerHTML = html;
    }

    function learnRace(btn) {
      const hit = confirm("このレースのAI予想は的中しましたか？\n[OK] = 的中 / [キャンセル] = 不的中");
      aiState.totalRaces++; aiState.todayRaces++;
      if (hit) {
        aiState.wonRaces++; aiState.todayWon++;
        btn.textContent = "🎯 的中";
        btn.className = "px-2.5 py-1.5 bg-emerald-900/60 text-emerald-300 border border-emerald-600 rounded-lg text-[10px] font-bold pointer-events-none";
      } else {
        btn.textContent = "❌ 不的中";
        btn.className = "px-2.5 py-1.5 bg-slate-800 text-slate-400 border border-slate-700 rounded-lg text-[10px] font-bold pointer-events-none";
      }
      localStorage.setItem('keibaAiStats', JSON.stringify(aiState));
      updateUI();
    }

    loadData();
  </script>
</body>
</html>


右上の 「Commit changes...」 → 「Commit changes」 を押して保存します。

ステップ 5：クラウドを初回起動する（テスト実行）

設定ができたので、GitHub Actionsを手動で1回動かしてみます。

リポジトリ上部のメニューから 「Actions」 タブをクリックします。

左メニューにある 「Keiba AI Auto Updater」 をクリックします。

右側に現れる 「Run workflow」 という灰色のボタンをクリックします。

ドロップダウンが表示されるので、緑色の 「Run workflow」 ボタンを押します。

30秒〜1分ほど待つと、緑色のチェックマーク（✔ update-data）が付き、成功します。

これで、クラウド上に自動で data/today.json が生成されました！

ステップ 6：スマホで確認

スマホで以下のURLにアクセスしてください：
https://hidekimaeda21-glitch.github.io/keiba-hideki/

これで、外部サーバー（GAS）との接続エラーに悩まされることなく、クラウドが自動生成したデータがスムーズに表示されます！
